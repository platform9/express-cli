#!/bin/bash

####################################################################################################
#
# Example:
#    Deploy and run cli against master
#         ./pf9ctl.sh
#    Local deployment using the current branch debugging enabled (DEVELOPMENT ONLY!)
#         ./pf9ctl.sh -l -d -b=$(git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')
#
####################################################################################################

set -o pipefail

start_time=$(date +"%s.%N")

assert() {
    if [ $# -gt 0 ]; then stdout_log "ASSERT: ${1}"; fi
    if [[ -f ${log_file} ]]; then
        echo -e "\n\n"
	echo ""
	echo "Installation failed, Here are the last 10 lines from the log"
	echo "The full installation log is available at ${log_file}"
	echo "If more information is needed re-run the install with --debug"
	echo "$(tail ${log_file})"
    else
	echo "Installation failed prior to log file being created"
	echo "Try re-running with --debug"
	echo "Installation instructions: https://docs.platform9.com/kubernetes/PMK-CLI/#installation"
    fi
    exit 1
}

debugging() {
    if [[ ${debug_flag} ]]; then stdout_log "${1}"; fi
}

stdout_log(){
    if [[ ${debug_flag} ]]; then
	if (which bc > /dev/null 2>&1); then
	    output="DEBUGGING: $(date +"%T") : $(bc <<<$(date +"%s.%N")-${start_time}) :$(basename $0) : ${1}"
	else
	    output="DEBUGGING: $(date +"%T") : $(basename $0) : ${1}"
	fi
        echo "${output}" 2>&1 | tee -a ${log_file}
    else
        echo "$1" 2>&1 | tee -a ${log_file}
    fi
}

parse_args() {
    for i in "$@"; do
      case $i in
	-h|--help)
	    echo "Usage: $(basename $0)"
#	    echo "	  [--branch=]"
#	    echo "	  [--dev] Installs from local source code for each project in editable mode."
#	    echo "                This assumes you have provided all source code in the correct locations"
#	    echo "	  [--local] Installs local source code in the same directory"
#	    echo "	  [-d|--debug]"
#	    echo ""
	    echo ""
	    exit 0
	    shift
	    ;;
	--branch=*)
	    if [[ -n ${i#*=} ]]; then
	      branch="${i#*=}"
	    else
		assert "'--branch=' Requires a Branch name"
	    fi
	    shift
	    ;;
	-d|--debug)
	    debug_flag="${i#*=}"
	    shift
	    ;;
	--dev)
	    dev_build="--dev"
	    shift
	    ;;
	--local)
	    run_local="--local"
	    shift
	    ;;
	*)
	echo "$i is not a valid command line option."
	echo ""
	echo "For help, please use $0 -h"
	echo ""
	exit 1
	;;
	esac
	shift
    done
}

init_venv_python() {
    debugging "Virtualenv: ${venv} doesn't not exist, Configuring."
    for ver in {3,2,''}; do #ensure python3 is first
	debugging "Checking Python${ver}: $(which python${ver})"
        if (which python${ver} > /dev/null 2>&1); then
	    python_version="$(python${ver} <<< 'import sys; print(sys.version_info[0])')"
	    stdout_log "Python Version Selected: python${python_version}"
	    break
        fi
    done

    if [[ ${python_version} == 2 ]]; then
        pyver="";
    else
        pyver="3";
    fi
    stdout_log "Initializing Virtual Environment using Python ${python_version}"
    #Validate and initialize virtualenv
    if ! (virtualenv --version > /dev/null 2>&1); then
        debugging "Validating pip"
	if ! which pip > /dev/null 2>&1; then
            debugging "ERROR: missing package: pip (attempting to install using get-pip.py)"
            curl -s -o ${pip_path} ${pip_url}
            if [ ! -r ${pip_path} ]; then assert "failed to download get-pip.py (from ${pip_url})"; fi

            if ! (python${pyver} "${pip_path}"); then
                debugging "ERROR: failed to install package: pip (attempting to install via 'sudo get-pip.py')"
                if (sudo python${pyver} "${pip_path}" > /dev/null 2>&1); then
                    assert "Please install package: pip"
                fi
            fi
        fi
	debugging "ERROR: missing python package: virtualenv (attempting to install via 'pip install virtualenv')"
        # Attemping to Install virtualenv
        if ! (pip${pyver} install virtualenv > /dev/null 2>&1); then
            debugging "ERROR: failed to install python package (attempting to install via 'sudo pip install virtualenv')"
            if ! (sudo pip${pyver} install virtualenv > /dev/null 2>&1); then
                assert "Please install the 'virtualenv' module using 'pip install virtualenv'"
            fi
        fi
    fi
    if ! (virtualenv -p python${pyver} ${venv} > /dev/null 2>&1); then assert "Creation of virtual environment failed"; fi
    debugging "venv_python: ${venv_python}"
    if [ ! -r ${venv_python} ]; then assert "failed to initialize virtual environment"; fi
}

initialize_basedir() {
    debugging "Initializing: ${pf9_basedir}"
    if [[ -n "${init_flag}" ]]; then
      debugging "DELETEING pf9_basedir: ${pf9_basedir}"
      if [ -d "${pf9_basedir}" ]; then
        rm -rf "${pf9_basedir}"
        if [ -d "${pf9_basedir}" ]; then assert "failed to remove ${pf9_basedir}"; fi
      fi
    fi
    debugging "Ensuring ${pf9_basedir} Exist"
    if ! mkdir -p "${pf9_basedir}" > /dev/null 2>&1; then assert "failed to create directory: ${pf9_basedir}"; fi
    debugging "Ensuring $(dirname ${log_file}) Exist"
    if ! mkdir -p "$(dirname ${log_file})" > /dev/null 2>&1; then assert "failed to create log directory: $(dirname ${log_file})"; fi
    debugging "Ensuring ${log_file} Exist"
    if ! touch "${log_file}" > /dev/null 2>&1; then assert "failed to create log file: ${log_file}"; fi
    debugging "Ensuring $(dirname ${pf9_bin}) Exist"
    if ! mkdir -p "${pf9_bin}" > /dev/null 2>&1; then assert "failed to create bin directory: $(dirname ${pf9_bin})"; fi
    if [ ! -d "${pf9_basedir}" ]; then assert "failed to create directory: ${pf9_basedir}"; fi
}




## main

parse_args "$@"
# Set global variables
if [ -z ${branch} ]; then branch=master; fi
debugging "Setting environment variables to be passed to installers"

if [[ -z ${run_local} && -z ${dev_build} ]]; then
    cli_url="git+git://github.com/platform9/express-cli.git@${branch}#egg=express-cli"
elif [[ -n ${dev_build} ]]; then
    cli_url="-e .[test]"
elif [[ -n ${run_local} ]]; then
    cli_url="."
    export CLI_LOCAL_SRC='True'
fi

debugging "CLFs: $*"
debugging "branch: ${branch}"
debugging "cli_url: ${cli_url}"
# Set the path so double quotes don't use the litteral '~'
pf9_basedir=$(dirname ~/pf9/.)
pip_path=${pf9_basedir}/get_pip.py
log_file=${pf9_basedir}/log/cli_install.log
pf9_bin=${pf9_basedir}/bin
venv="${pf9_basedir}/pf9-venv"
venv_python="${venv}/bin/python"
venv_activate="${venv}/bin/activate"
pip_url="https://bootstrap.pypa.io/get-pip.py"
cli_entrypoint=$(dirname ${venv_python})/express
cli_exec=${pf9_bin}/pf9ctl


# initialize installation directory
initialize_basedir

# configure python virtual environment
stdout_log "Configuring virtualenv"
if [ ! -f "${venv_activate}" ]; then
    init_venv_python
else
    stdout_log "INFO: using exising virtual environment"
fi

debugging "Upgrade pip"
if ! (${venv_python} -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1); then
    assert "Pip upgrade failed"; fi

stdout_log "Installing Platform9 Express Management Suite"
if ! (${venv_python} -m pip install --upgrade ${cli_url} > debugging); then
    assert "Installation of Platform9 Express CLI Failed"; fi

#stdout_log "Installing Platform9 Express Management Environment"
#if ! (${cli_entrypoint} init > /dev/null 2>&1); then
#    assert "Initialization of Platform9 Express-CLI Failed"; fi
if [ ! -f ${cli_exec} ]; then
    debugging "Create Express-CLI symlink"
    if ! (ln -s ${cli_entrypoint} ${cli_exec} > /dev/null 2>&1); then
	    assert "failed to create Express-CLI symlink: ${cli_exec}"; fi
fi


# Code executes clean but is updating path in subshell
if [[ -d "${pf9_bin}" ]]; then
    debugging "echo $PATH | grep -q ${pf9_bin}"
    if ! echo "$PATH" | grep -q "${pf9_bin}"; then
	debugging "Adding ${pf9_bin} to '$PATH'"
	eval export PATH="${pf9_bin}:$PATH"
    fi
fi
echo "Please provide your Platform9 Credentials:"
eval "${cli_exec}" config create
eval "${cli_exec}" config validate
echo "Please find the pf9ctl documentation here: https://docs.platform9.com/kubernetes/PMK-CLI/"

echo "To start building a Kubernetes cluster: $ ${cli_exec} cluster --help"
echo ""
eval "${cli_exec}" cluster --help

# Need to add path to user's bash profile or bashrc
# Launch wizard -t and CLI --version > /dev/null 2>&1 to ensure they are good to go.
# Need to Build Dump Screen (What you are left with Post Install)
# Should have option (or different filename that launches CLI onboarding)
