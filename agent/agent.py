#!/bin/env python

# Copyright 2016, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

# External dependencies
import PIL.Image

# Python standard library
import argparse

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import datetime
import errno
import json
import slycat.mime_type
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import uuid
import abc
import logging
import ConfigParser

session_cache = {}


class Agent(object):
    """
    This class is an interface for agent functionality on a cluster server
    """
    __metaclass__ = abc.ABCMeta
    _log_lock = threading.Lock()
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(logging.FileHandler('slycat-agent.log'))
    log.handlers[0].setFormatter(logging.Formatter("[%(asctime)s] - [%(levelname)s] : %(message)s"))
    @abc.abstractmethod
    def run_remote_command(self, command):
        """
        command to be run on the remote machine
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def launch(self, command):
        """
        launch a job on the remote machine
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def submit_batch(self, command):
        """
        submit a batch job on the remote machine
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def checkjob(self, command):
        """
        check a job's status on a remote machine
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def cancel_job(self, command):
        """
        cancels a remote job
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def get_job_output(self, command):
        """
        get a detailed version of the jobs output
        :param command: json command
        :return: 
        """
        pass

    @abc.abstractmethod
    def generate_batch(self, module_name, wckey, nnodes, partition, ntasks_per_node, time_hours, time_minutes,
                       time_seconds,
                       fn,
                       tmp_file):
        """
        generate a remote batch file that can be used
        by the remote system's mpi queue
        :param module_name: 
        :param wckey: 
        :param nnodes: 
        :param partition: 
        :param ntasks_per_node: 
        :param time_hours: 
        :param time_minutes: 
        :param time_seconds: 
        :param fn: 
        :param tmp_file: 
        :return: 
        """
        pass

    @abc.abstractmethod
    def run_function(self, command):
        """
        function used to run a job
        :param command: json command
        :return: 
        """
        pass

    def get_user_config(self):
        """
        reads the users config as json 
        {results:{config:{}, "ok":bool, errors:"string errors message"}}
        :return: 
        """
        results = {
            "ok": True
        }

        rc = os.path.expanduser('~') + "/.slycatrc"
        if os.path.isfile(rc):
            try:
                parser = ConfigParser.RawConfigParser()
                parser.read(rc)
                configuration = {section: {key: eval(value) for key, value in parser.items(section)} for section in
                                 parser.sections()}
                results["config"] = configuration
                results["errors"] = ""
            except Exception as e:
                results["config"] = {}
                results["errors"] = "%s" % e
        else:
            results["config"] = "see errors"
            results["errors"] = "the user does not have a .slycatrc file under their home directory"

        sys.stdout.write("%s\n" % json.dumps(results))
        sys.stdout.flush()

    def set_user_config(self, command):
        """
        writes config into ~/.slycatrc file of the user
        :param command: incoming json format should be 
        {
        action:"action",
        command:{config:{section_key:{option_key:"value"}...}}
        }
        :return: 
        """
        results = {
            "ok": True,
            "errors": ""
        }
        config = command["command"]["config"]
        rc = os.path.expanduser('~') + "/.slycatrc"

        with open(rc, "w+") as rc_file:
            rc_file.seek(0)
            rc_file.truncate()
            parser = ConfigParser.RawConfigParser()
            for section_key in config:
                if not parser.has_section(section_key):
                    parser.add_section(section_key)
                section = config[section_key]
                for option_key in section:
                    if not str(section[option_key]) == "":
                        parser.set(section_key, option_key, "\"%s\"" % section[option_key])
            parser.write(rc_file)
        sys.stdout.write("%s\n" % json.dumps(results))
        sys.stdout.flush()

    # Handle the 'browse' command.
    def browse(self, command):
        if "path" not in command:
            raise Exception("Missing path.")
        path = command["path"]
        if not os.path.isabs(path):
            raise Exception("Path must be absolute.")
        if not os.path.exists(path):
            raise Exception("Path not found.")

        file_reject = re.compile(command.get("file-reject")) if "file-reject" in command else None
        file_allow = re.compile(command.get("file-allow")) if "file-allow" in command else None
        directory_reject = re.compile(command.get("directory-reject")) if "directory-reject" in command else None
        directory_allow = re.compile(command.get("directory-allow")) if "directory-allow" in command else None

        if os.path.isdir(path):
            names = sorted(os.listdir(path))
        else:
            path, name = os.path.split(path)
            names = [name]

        listing = {
            "ok": True,
            "path": path,
            "names": [],
            "sizes": [],
            "types": [],
            "mtimes": [],
            "mime-types": [],
        }

        for name in names:
            fpath = os.path.join(path, name)
            fstat = os.stat(fpath)
            ftype = "d" if stat.S_ISDIR(fstat.st_mode) else "f"

            if ftype == "d":
                if directory_reject is not None and directory_reject.search(fpath) is not None:
                    if directory_allow is None or directory_allow.search(fpath) is None:
                        continue

            if ftype == "f":
                if file_reject is not None and file_reject.search(fpath) is not None:
                    if file_allow is None or file_allow.search(fpath) is None:
                        continue

            if ftype == "d":
                mime_type = "application/x-directory"
            else:
                mime_type = slycat.mime_type.guess_type(name)[0]

            listing["names"].append(name)
            listing["sizes"].append(fstat.st_size)
            listing["types"].append(ftype)
            listing["mtimes"].append(datetime.datetime.fromtimestamp(fstat.st_mtime).isoformat())
            listing["mime-types"].append(mime_type)

        sys.stdout.write("%s\n" % json.dumps(listing))
        sys.stdout.flush()

    # Handle the 'get-file' command.
    def get_file(self, command):
        if "path" not in command:
            raise Exception("Missing path.")
        path = command["path"]
        if not os.path.isabs(path):
            raise Exception("Path must be absolute.")
        if not os.path.exists(path):
            raise Exception("Path not found.")
        if not os.access(path, os.R_OK):
            raise Exception("No read permission.")
        if os.path.isdir(path):
            raise Exception("Directory unreadable.")

        try:
            content = open(path, "rb").read()
        except IOError as e:
            if e.errno == errno.EACCES:
                raise Exception("Access denied.")
            raise Exception(e.strerror)
        except Exception as e:
            raise Exception(e.message)

        content_type, encoding = slycat.mime_type.guess_type(path)
        sys.stdout.write("%s\n%s" % (json.dumps(
            {"ok": True, "message": "File retrieved.", "path": path, "content-type": content_type,
             "size": len(content)}),
                                     content))
        sys.stdout.flush()

    # Handle the 'get-image' command.
    def get_image(self, command):
        if "path" not in command:
            raise Exception("Missing path.")
        path = command["path"]
        if not os.path.isabs(path):
            raise Exception("Path must be absolute.")
        if not os.path.exists(path):
            raise Exception("Path not found.")
        if os.path.isdir(path):
            raise Exception("Directory unreadable.")

        file_content_type, encoding = slycat.mime_type.guess_type(path)
        requested_content_type = command.get("content-type", file_content_type)

        # Optional fast path if the client hasn't requested anything that would alter the image contents:
        if "max-size" not in command and "max-width" not in command and "max-height" not in command and requested_content_type == file_content_type:
            try:
                content = open(path, "rb").read()
            except IOError as e:
                if e.errno == errno.EACCES:
                    raise Exception("Access denied.")
                raise Exception(e.strerror)
            except Exception as e:
                raise Exception(e.message)

            content_type, encoding = slycat.mime_type.guess_type(path)
            sys.stdout.write("%s\n%s" % (json.dumps(
                {"ok": True, "message": "Image retrieved.", "path": path, "content-type": content_type,
                 "size": len(content)}), content))
            sys.stdout.flush()
            return

        if requested_content_type not in ["image/jpeg", "image/png"]:
            raise Exception("Unsupported image type.")

        # Load the requested image.
        try:
            image = PIL.Image.open(path)
        except IOError as e:
            raise Exception(e.strerror)

        # Optionally downsample the image.
        size = image.size
        if "max-size" in command:
            size = (command["max-size"], command["max-size"])
        if "max-width" in command:
            size = (command["max-width"], size[1])
        if "max-height" in command:
            size = (size[0], command["max-height"])
        if size != image.size:
            image.thumbnail(size=size, resample=PIL.Image.ANTIALIAS)

        # Save the image to the requested format.
        content = StringIO.StringIO()
        if requested_content_type == "image/jpeg":
            image.save(content, "JPEG")
        elif requested_content_type == "image/png":
            image.save(content, "PNG")

        # Send the results back to the caller.
        sys.stdout.write("%s\n%s" % (json.dumps(
            {"ok": True, "message": "Image retrieved.", "path": path, "content-type": requested_content_type,
             "size": len(content.getvalue())}), content.getvalue()))
        sys.stdout.flush()

    def run(self):
        """
        format {action:action, command: command}
        :return: 
        """
        self.log.info("\n")
        self.log.info("*agent started*")
        # Parse and sanity-check command-line arguments.
        parser = argparse.ArgumentParser()
        parser.add_argument("--fail-startup", default=False, action="store_true",
                            help="Fail immediately on startup.  Obviously, this is for testing.")
        parser.add_argument("--fail-exit", default=False, action="store_true",
                            help="Fail during exit.  Obviously, this is for testing.")
        arguments = parser.parse_args()

        if arguments.fail_startup:
            exit(-1)

        # Let the caller know we're ready to handle commands.
        sys.stdout.write("%s\n" % json.dumps({"ok": True, "message": "Ready."}))
        sys.stdout.flush()

        while True:
            # format: {"action":"action"}
            # Read the next command from caller.
            command = sys.stdin.readline()
            if command == "":  # EOF means the caller went away and it's time to shut-down.
                break

            try:
                # Parse the command, which must be a JSON object containing an action.
                try:
                    command = json.loads(command)
                except:
                    self.log.error("Not a JSON object.")
                    raise Exception("Not a JSON object.")
                if not isinstance(command, dict):
                    self.log.error("Not a JSON object.")
                    raise Exception("Not a JSON object.")
                if "action" not in command:
                    self.log.error("Missing action for command: %s" % command)
                    raise Exception("Missing action.")

                action = command["action"]
                self.log.info("command: %s" % command)
                if action == "exit":
                    self.log.info("*agent stopping*\n")
                    if not arguments.fail_exit:
                        break
                elif action == "browse":
                    self.browse(command)
                elif action == "get-file":
                    self.get_file(command)
                elif action == "get-image":
                    self.get_image(command)
                elif action == "create-video":
                    sys.stdout.write("%s\n" % json.dumps({"ok": False, "message": "this command is depricated and has "
                                                                                  "been removed"}))
                    sys.stdout.flush()
                elif action == "video-status":
                    self.video_status(command)
                elif action == "launch":
                    self.launch(command)
                elif action == "submit-batch":
                    self.submit_batch(command)
                elif action == "checkjob":
                    self.checkjob(command)
                elif action == "get-job-output":
                    self.get_job_output(command)
                elif action == "run-function":
                    self.run_function(command)
                elif action == "cancel-job":
                    self.cancel_job(command)
                elif action == "get-user-config":
                    self.get_user_config()
                elif action == "set-user-config":
                    self.set_user_config(command)
                else:
                    self.log.error("Unknown command.")
                    raise Exception("Unknown command.")
            except Exception as e:
                sys.stdout.write("%s\n" % json.dumps({"ok": False, "message": e.message}))
                sys.stdout.flush()


if __name__ == "__main__":
    """
    this is how we run the agent when implemented
    """
    some_cluster_agent = Agent()
    some_cluster_agent.run()
