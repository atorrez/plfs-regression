#!/usr/bin/env python
#
# Test rename in plfs. Uses fuse interface.

import os,sys,getpass,re,datetime,subprocess
from time import localtime, strftime, sleep

user = getpass.getuser()

# Figure out the base directory of the regression suite
curr_dir = os.getcwd()
basedir = re.sub('tests/truncate_open_file.*', '', curr_dir)

# Add the directory that contains the helper scripts
utils_dir = basedir + "tests/utils"
if utils_dir not in sys.path:
    sys.path += [ utils_dir ]

# Add the module that will help get plfs mount points
import rs_plfs_config_query as pcq

# Set up the right environment
import rs_env_init

# Import the module for dealing with experiment_management paths
import rs_exprmgmt_paths_add as emp
# Add the experiment_management location to sys.path
emp.add_exprmgmt_paths(basedir)
import expr_mgmt

import rs_exprmgmtrc_target_path_append as tpa

class plfsMntError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return str(self.msg)

def main(argv=None):
    """Main method for running this test.

    Return values:
     0: Test ran
    -1: Problem with opening the log file.
    """
    # Where the output of the test will be placed.
    out_dir = (str(expr_mgmt.config_option_value("outdir")) + "/"
        + str(datetime.date.today()))
    # Create the directory if needed
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out_file = (str(out_dir) + "/" + str(strftime("%H-%M-%S", localtime())) + ".log")
    try:
        of = open(out_file, 'w')
    except OSError, detail:
        print ("Error: unable to create log file " + str(out_file) + ": " + str(detail))
        return [ -1 ]
        
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = of
    sys.stderr = of
    
    # Set up paths to plfs install directories
    rs_env_init.add_plfs_paths(basedir)

    # Test status. This will be printed out at the end and will be used to
    # determine if the test passed when check_results.py is called.
    test_stat = "FAILED"

    try:
        # Get a mount point
        mount_points = pcq.get_mountpoints()
        if len(mount_points) > 0:
            mount_point = mount_points[-1]
        else:
            raise plfsMntError("unable to get mount point.\n")

        # Check for rs_mnt_append_path in experiment_management
        top_dir = tpa.append_path([mount_point])[0]
        # Define two targets
        file1 = str(curr_dir) + "/truncate_o_control"
        file2 = str(top_dir) + "/" + os.getenv("MY_MPI_HOST") + ".truncate_o_test"

        # variable to keep track of if we need to issue the unmount command.
        need_to_umount = True
       
        # Mount the plfs mount point
        print("Mounting " + str(mount_point))
        # Flush the output so that the output in the file is somewhat
        # consistent in time.
        sys.stdout.flush()
        sys.stderr.flush() 
        p = subprocess.Popen([str(utils_dir) + '/rs_plfs_fuse_mount.sh '
            + str(mount_point) + ' serial'], stdout=of, stderr=of, shell=True)
        p.communicate()
        if p.returncode == 0:
            print (str(mount_point) + " successfully mounted")
            need_to_umount = True
        elif p.returncode == 1:
            # This script will not issue the unmount command if
            # rs_plfs_fuse_mount.sh returns with a 1.
            print (str(mount_point) + " already mounted")
            need_to_umount = False
        else:
            raise plfsMntError("problem with mounting\nExiting.\n")
        
        sys.stdout.flush()
        sys.stderr.flush() 
        
        # Call the truncate_open_file.bash script with the two files
        p = subprocess.Popen(['./truncate_open_file.bash ' + str(file1)
            + ' ' + str(file2)], stdout=of, stderr=of, shell=True)
        p.communicate()
        if p.returncode == 0:
            test_stat = "PASSED"
        
        # Unmount the plfs mount point
        if need_to_umount == True:
            sys.stdout.flush()
            sys.stderr.flush()
            print ("Unmounting " + str(mount_point))
            sys.stdout.flush()
            sys.stderr.flush()
            p = subprocess.Popen([str(utils_dir) + '/rs_plfs_fuse_umount.sh '
                + str(mount_point) + ' serial'], stdout=of, stderr=of, shell=True)
            p.communicate()
            if p.returncode != 0:
                # Couldn't unmount; treat this as an error.
                raise plfsMntError("Unable to unmount " + str(mount_point) + "\n")
            else:
                print ("Successfully unmounted " + str(mount_point))

    except plfsMntError, detail:
        print("Problem dealing with plfs mounts: " + str(detail))
    else:
        print("The test " + str(test_stat))
    finally:
        # Close up shop
        sys.stdout.flush()
        sys.stderr.flush()
        of.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        # If we're here, we're done. We don't know if the test passed, but that
        # doesn't matter; it will be check_tests.py job to determine that. Let
        # the calling process know that it needs to check results of this test.
        return [ 0 ]

if __name__ == "__main__":
    ret = main()
    # ret is a list, so we don't want to just return it. At this point, we just
    # return a 0.
    sys.exit(0)
