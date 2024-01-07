# file_hosting_service

File Hosting Service for Distributed Systems at the UPV/EHU

This repository contains two main versions of the proof of concept for a cloud file service:

- *artefact_single-server*: This is the first and original version of the file hosting service. It was designed to work with a single replication server that syncs the changes made to the specified local folders with the remote server.
- *active_replication*: This version of the service is the most recent one and adapts the previously developed code to work with multiple instead of only a single remote servers. The fundamental behavior, however, is still the same and the primary adaptation that was made is the implementation of the active replication mechanism.