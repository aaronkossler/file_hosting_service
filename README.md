# file_hosting_service
File Hosting Service for Distributed Systems at the UPV/EHU, Group tag KT

## 1. Quick Start Guide
1. Clone the Github repository to your local machine for both client and server.
2. Run pip install -r requirements.txt in order to install all required dependencies.
3. Check/modify the parameters via the config.json files or the command line parameters (also accessible via python3 client.py –help).
4. Start the server program first and any clients that want to connect afterwards.
5. Log in as the client (e.g. with the sar/sar information).
6. Start synching by adding files to the specified directory.

For more details, refer to the chapters listed below.

## 2. Deployment

### 2.1 Requirements

#### 2.1.1 Operating System
The service has been successfully tested on Linux Ubuntu and Windows 11, which are the recommended operating systems to use.
Note: On Windows 11, the exit handling is currently not completely functional. The main functionality is still provided.

#### 2.1.2 Software
The service runs on Python 3, which is required to host the service on the user's machine and to use it. It has been tested on Python 3.10, but other versions should not cause any issues. The latest Python version can be downloaded here. In addition, a list of python packages are necessary to install.

Package name, Version
watchdog, 3.0.0
pandas, 2.1.1
maskpass, 0.3.7

Packages can be installed through pip, which is an installer, which comes prepackaged with python. In order to install a package, the user should execute the following command:
pip install <package_name>==<version_number>

Alternatively, navigate to the project folder and install all requirements via:
pip install -r requirements.txt

#### 2.1.3 IP address space and ports
Since the user can decide through which server address and port should be used for communication, it has to be made sure that the IP address is reachable, connection to the network is established, and the port is free for the chosen connection protocol (e.g. ssh). In the UPV Lab 1.8, the ports 5000 to 5200 are usable for such a connection.

### 2.2 Starting the program
#### 2.2.1 Parameters
The following parameters can be set for the client and server programs:

Argument, Description
--client-dir/--server-dir The directory, which should be used for the service (where the data is synchronized)
--server-host The host address of the server
--server-port The port number of the server
--debug Used to turn on debugging, primarily logging the sent messages between client and server

It is up to the user whether he wants to do that via cmd line arguments or in the respective config.json file.
Note: The folder that is referred to in the first parameter should already exist!

#### 2.2.2 Setup Server
To start the server, the user should have the “server” folder as well as the “resources” folder of the code base on the desired machine to be used as a server. The user should navigate into the folder through the command line and run the following command:

python3 server.py 	[--server-dir <server_directory>]
[--server-host <server_host_address>]
[--server-port <server_port_number>]
[-- debug /or nothing]

If the server started successfully, the following output should be visible:
Server listening on <server_address>:<server_port>

#### 2.2.3 Setup Client
To start a client, the user should have the “client” folder as well as the “resources” folder of the code base on the desired machine to be used as a client. The user should navigate into the folder through the command line and run the following command:

python3 client.py 	[--client-dir <client_directory>]
[--server-host <server_host_address>]
[--server-port <server_port_number>]
[-- debug /or nothing]

If the client connected successfully, the following output should be visible on the client side:
Connected to <server_address>:<server_port>

The following output should be displayed on the server side:
Accepted connection from ('<client_address>', <client_port>)

Now that a connection between the client and server is established, the client can log into one of the user accounts. The client will ask the user to enter the username with the corresponding password:
Enter username: <username>
Password: <password>

After a successful login, the client should show the following output:
Logged in successfully

The following output should be visible on the server side:
Login successful by ('<client_address>', <client_port>)

## 3. Usage
If the user has established a connection between the server and client, the service is now ready for usage.

To start using the service, the user is free to use tools with a GUI such as the built in Windows Explorer or Nautilus (Files) to create, modify and delete files and directories, but can also use the command line.

In the latter case, the user should open a new command line window and navigate to the directory entered as an argument for --client-dir.

## 4. Shutdown
### 4.1 Server
In order to shut down the server, the user can press Ctrl+C in the command line window of the server, which is also known as the KeyboardInterrupt command. This will shut down the server as well as all connected clients.

The following output should be displayed on the server side:
Server terminated

On the client side, the command line should show:
Server is disconnected. Closing client...

### 4.2 Client
In order to shut down a client, the user can press Ctrl+C in the command line window of the client.

The following output should be displayed on the client side:
Closing client…

The server should show the following output:
('<client_address>', <client_port>) disconnected

