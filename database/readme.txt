This folder contains a backup of the database which should be created on the brain.

To restore the database you can use:

    mysql -u root -p robotAI < /var/lib/mysql/robotAI.bak

You may need to create thye ndatab ase first in mysql. Login to mysql with:

    mysql -u root -p
    
Then run the following command at the mysql> cursor

    create database robotAI;
