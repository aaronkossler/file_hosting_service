#!/usr/bin/env python3

import os
import socket
import sys

import szasar

SERVER = 'localhost'
PORT = 6012
ER_MSG = (
    "Correct.",
    "Unknown or unexpected command.",
    "Unknown user.",
    "Incorrect password.",
    "Error creating file list.",
    "File does not exist.",
    "Error downloading file.",
    "An anonymous user does not have permission for this operation.",
    "The file is too large.",
    "Error preparing file for upload.",
    "Error uploading file.",
    "Error deleting file.")


class Menu:
    List, Download, Upload, Delete, Exit = range(1, 6)
    Options = (
        "File list",
        "Download file",
        "Upload file",
        "Delete file",
        "Exit")

    def menu():
        print("+{}+".format('-' * 30))
        for i, option in enumerate(Menu.Options, 1):
            print("| {}.- {:<25}|".format(i, option))
        print("+{}+".format('-' * 30))

        while True:
            try:
                selected = int(input("Select an option: "))
            except:
                print("Invalid option.")
                continue
            if 0 < selected <= len(Menu.Options):
                return selected
            else:
                print("Invalid option.")


def iserror(message):
    if message.startswith("ER"):
        code = int(message[2:])
        print(ER_MSG[code])
        return True
    else:
        return False


def int2bytes(n):
    if n < 1 << 10:
        return str(n) + " B  "
    elif n < 1 << 20:
        return str(round(n / (1 << 10))) + " KiB"
    elif n < 1 << 30:
        return str(round(n / (1 << 20))) + " MiB"
    else:
        return str(round(n / (1 << 30))) + " GiB"


if __name__ == "__main__":
    if len(sys.argv) > 3:
        import sys

        print("Usage: {} [<server> [<port>]]".format(sys.argv[0]))
        exit(2)

    if len(sys.argv) >= 2:
        SERVER = sys.argv[1]
    if len(sys.argv) == 3:
        PORT = int(sys.argv[2])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER, PORT))

    while True:
        user = input("Enter username: ")
        message = "{}{}\r\n".format(szasar.Command.User, user)
        s.sendall(message.encode("ascii"))
        message = szasar.recvline(s).decode("ascii")
        if iserror(message):
            continue

        password = input("Enter password: ")
        message = "{}{}\r\n".format(szasar.Command.Password, password)
        s.sendall(message.encode("ascii"))
        message = szasar.recvline(s).decode("ascii")
        if not iserror(message):
            break

    while True:
        option = Menu.menu()

        if option == Menu.List:
            message = "{}\r\n".format(szasar.Command.List)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            if iserror(message):
                continue
            filecount = 0
            print("List of available files")
            print("-------------------------------")
            while True:
                line = szasar.recvline(s).decode("ascii")
                if line:
                    filecount += 1
                    fileinfo = line.split('?')
                    print("{:<20} {:>8}".format(fileinfo[0],
                                                int2bytes(int(fileinfo[1]))))
                else:
                    break
            print("-------------------------------")
            if filecount == 0:
                print("There are no available files.")
            else:
                plural = "s" if filecount > 1 else ""
                print("{0} file{1} available{1}.".format(filecount, plural))

        elif option == Menu.Download:
            filename = input("Enter the file you want to download: ")
            message = "{}{}\r\n".format(szasar.Command.Download, filename)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            if iserror(message):
                continue
            filesize = int(message[2:])
            message = "{}\r\n".format(szasar.Command.Download2)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            if iserror(message):
                continue
            filedata = szasar.recvall(s, filesize)
            try:
                with open(filename, "wb") as f:
                    f.write(filedata)
            except:
                print("The file could not be saved to disk.")
            else:
                print("The file {} has been downloaded successfully.".format(
                    filename))

        elif option == Menu.Upload:
            filename = input("Enter the file you want to upload: ")
            try:
                filesize = os.path.getsize(filename)
                with open(filename, "rb") as f:
                    filedata = f.read()
            except:
                print("The file {} could not be accessed.".format(filename))
                continue

            message = "{}{}?{}\r\n".format(szasar.Command.Upload, filename,
                                           filesize)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            if iserror(message):
                continue

            message = "{}\r\n".format(szasar.Command.Upload2)
            s.sendall(message.encode("ascii"))
            s.sendall(filedata)
            message = szasar.recvline(s).decode("ascii")
            if not iserror(message):
                print("The file {} has been sent successfully.".format(
                    filename))

        elif option == Menu.Delete:
            filename = input("Enter the file you want to delete: ")
            message = "{}{}\r\n".format(szasar.Command.Delete, filename)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            if not iserror(message):
                print("The file {} has been deleted successfully.".format(
                    filename))

        elif option == Menu.Exit:
            message = "{}\r\n".format(szasar.Command.Exit)
            s.sendall(message.encode("ascii"))
            message = szasar.recvline(s).decode("ascii")
            break
    s.close()
