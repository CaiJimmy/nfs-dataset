"""This profile sets up a simple NFS server and a network of clients. The NFS server uses
a long term dataset that is persistent across experiments. In order to use this profile,
you will need to create your own dataset and use that instead of the demonstration
dataset below. If you do not need persistant storage, we have another profile that
uses temporary storage (removed when your experiment ends) that you can use.

Instructions:
Click on any node in the topology and choose the `shell` menu item. Your shared NFS directory is mounted at `/nfs` on all nodes.
"""

# Import the Portal object.
import geni.portal as portal

# Import the ProtoGENI library.
import geni.rspec.pg as pg

# Import the Emulab specific extensions.
import geni.rspec.emulab as emulab

# Create a portal context.
pc = portal.Context()

# Create a Request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Only Ubuntu images supported.
imageList = [
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU24-64-STD", "UBUNTU 24.04"),
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD", "UBUNTU 22.04"),
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD", "UBUNTU 20.04"),
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU18-64-STD", "UBUNTU 18.04"),
    (
        "urn:publicid:IDN+emulab.net+image+emulab-ops//CENTOS9S-64-STD",
        "CENTOS Stream 9",
    ),
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//FBSD135-64-STD", "FreeBSD 13.5"),
    ("urn:publicid:IDN+emulab.net+image+emulab-ops//FBSD142-64-STD", "FreeBSD 14.2"),
]

# Do not change these unless you change the setup scripts too.
nfsServerName = "nfs"
nfsLanName = "nfsLan"
nfsDirectory = "/nfs"

# Number of NFS clients (there is always a server)
pc.defineParameter(
    "clientCount", "Number of NFS clients", portal.ParameterType.INTEGER, 2
)

pc.defineParameter(
    "dataset",
    "Your dataset URN",
    portal.ParameterType.STRING,
    "urn:publicid:IDN+emulab.net:portalprofiles+ltdataset+DemoDataset",
)

pc.defineParameter(
    "osImage", "Select OS image", portal.ParameterType.IMAGE, imageList[1], imageList
)

# Optional physical type for all nodes.
pc.defineParameter(
    "phystype",
    "Optional physical node type",
    portal.ParameterType.NODETYPE,
    "",
    longDescription="Pick a single physical node type (pc3000,d710,etc) "
    + "instead of letting the resource mapper choose for you.",
)

pc.defineParameter(
    "client_phystype",
    "Optional client physical node type",
    portal.ParameterType.NODETYPE,
    "",
    longDescription="Pick a single physical node type (pc3000,d710,etc) "
    + "instead of letting the resource mapper choose for you.",
)

pc.defineParameter(
    "node_names",
    "Name of physical nodes, separated by comma (only applies to non-client nodes)",
    portal.ParameterType.STRING,
    "",
    longDescription="Node names, separated by comma",
)


# Always need this when using parameters
params = pc.bindParameters()

if params.phystype != "":
    tokens = params.phystype.split(",")
    if len(tokens) != 1:
        pc.reportError(
            portal.ParameterError("Only a single type is allowed", ["phystype"])
        )

if params.client_phystype != "":
    tokens = params.client_phystype.split(",")
    if len(tokens) != 1:
        pc.reportError(
            portal.ParameterError("Only a single type is allowed", ["client_phystype"])
        )

nodeNames = params.node_names.split(",") if params.node_names else []


# The NFS network. All these options are required.
nfsLan = request.LAN(nfsLanName)
nfsLan.best_effort = True
nfsLan.vlan_tagging = True
nfsLan.link_multiplexing = True

# The NFS server.
nfsServer = request.RawPC(nfsServerName)
nfsServer.disk_image = params.osImage

if params.phystype != "":
    nfsServer.hardware_type = params.phystype

# Attach server to lan.
nfsLan.addInterface(nfsServer.addInterface())
# Initialization script for the server
nfsServer.addService(
    pg.Execute(shell="sh", command="sudo /bin/bash /local/repository/nfs-server.sh")
)

# Special node that represents the ISCSI device where the dataset resides
dsnode = request.RemoteBlockstore("dsnode", nfsDirectory)
dsnode.dataset = params.dataset

# Link between the nfsServer and the ISCSI device that holds the dataset
dslink = request.Link("dslink")
dslink.addInterface(dsnode.interface)
dslink.addInterface(nfsServer.addInterface())
# Special attributes for this link that we must use.
dslink.best_effort = True
dslink.vlan_tagging = True
dslink.link_multiplexing = True

# The NFS clients, also attached to the NFS lan.
for i in range(1, params.clientCount):
    name = nodeNames[i - 1] if i - 1 < len(nodeNames) else "node%d" % i
    node = request.RawPC(name)
    node.disk_image = params.osImage

    if params.phystype != "":
        node.hardware_type = params.phystype
        pass

    nfsLan.addInterface(node.addInterface())
    # Initialization script for the clients
    node.addService(
        pg.Execute(shell="sh", command="sudo /bin/bash /local/repository/nfs-client.sh")
    )
    pass

# One of the nodes is the client
node = request.RawPC("client")
node.disk_image = params.osImage
node.hardware_type = params.client_phystype
nfsLan.addInterface(node.addInterface())
# Initialization script for the clients
node.addService(
    pg.Execute(shell="sh", command="sudo /bin/bash /local/repository/nfs-client.sh")
)


# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
