#!/bin/bash

####################################################################################################
#
# Example:
#    Deploy and run cli against master
#         ./cli-setup.sh
#    Deploy and run cli against master
#         ./cli-setup.sh
#    Local deployment using the current branch debugging enabled (DEVELOPMENT ONLY!)
#         ./cli-setup.sh -l -d -b=$(git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')
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
    # This function handles formatting all debugging text.
    # debugging is always sent to the logfile.
    # If no debug flag, this function will silently log debugging messages.
    # If debug flag is present then debug output will be formatted then echo'd to stdout and sent to logfile.
    # If debug flag is present messages sent to stdout_log will be forwarded to debugging for consistancy.

    # Avoid error if bc is not installed yet
    if (which bc > /dev/null 2>&1); then
	output="DEBUGGING: $(date +"%T") : $(bc <<<$(date +"%s.%N")-${start_time}) :$(basename $0) : ${1}"
    else
	output="DEBUGGING: $(date +"%T") : $(basename $0) : ${1}"
    fi

    if [ -f "${log_file}" ]; then
	echo "${output}" 2>&1 >> ${log_file}
    fi
    if [[ ${debug_flag} ]]; then
	echo "${output}"
    fi
}

stdout_log(){
    # If debug flag is present messages sent to stdout_log will be forwarded to debugging for consistancy.
    if [[ ${debug_flag} ]]; then
	debugging "$1"
    else
        echo "$1"
	debugging "$1"
    fi
}

parse_args() {
    while [ $# -gt 0 ]; do
        case ${1} in
            -h|--help)
                echo "Usage: $(basename $0)"
                #echo "	  [--branch=] Specify a different branch to pull Platform9 CLI source"
                #echo "	  [--dev] Installs from local source code for each project in editable mode."
                #echo "                This assumes you have provided all source code in the correct locations"
                #echo "	  [--local] Installs local source code in the same directory"
                echo "	  [-d|--debug] Uses debug verbosity during install"
                echo ""
                exit 0
                ;;
            --branch=*)
                if [[ -n ${1#*=} ]]; then
                branch="${1#*=}"
                else
                assert "'--branch=' Requires a Branch name"
                fi
                shift
                ;;
            -d|--debug)
                debug_flag="${1#*=}"
                shift
                ;;
            --install_only)
                install_only=TRUE
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
            --pf9_account_url)
                PF9_MGMTURL=${2}
                shift 2
                ;;
            --pf9_email)
                PF9_USER=${2}
                shift 2
                ;;
            --pf9_password)
                PF9_PASS=${2}
                shift 2
                ;;
            --pf9_region)
                PF9_REGION=${2}
                shift 2
                ;;
            --pf9_project)
                PF9_TENANT=${2}
                shift 2
                ;;
            *)
                echo "${1} is not a valid command line option."
                echo ""
                echo "For help, please use $0 -h"
                echo ""
                exit 1
                ;;
        esac
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
    if ! (${local_virtualenv} --version > /dev/null 2>&1); then
        debugging "Validating pip"
	if ! which ${local_pip} > /dev/null 2>&1; then
            debugging "ERROR: missing package: pip (attempting to install using get-pip.py)"
            curl -s -o ${pip_path} ${pip_url}
            if [ ! -r ${pip_path} ]; then assert "failed to download get-pip.py (from ${pip_url})"; fi

            if ! (python${pyver} "${pip_path}" --user); then
                debugging "ERROR: failed to install package: pip (attempting to install via 'sudo get-pip.py')"
                if (sudo python${pyver} "${pip_path}" --user > /dev/null 2>&1); then
                    assert "Please install package: pip"
                fi
            fi
        fi
	debugging "ERROR: missing python package: virtualenv (attempting to install via 'pip install virtualenv')"
        # Attemping to Install virtualenv
        if ! (${local_pip}${pyver} install virtualenv --user --ignore-installed > /dev/null 2>&1); then
            debugging "ERROR: failed to install python package (attempting to install via 'sudo pip install virtualenv')"
            if ! (sudo pip${pyver} install virtualenv --user --ignore-installed > /dev/null 2>&1); then
                assert "Please install the 'virtualenv' module using 'pip install virtualenv'"
            fi
        fi
    fi
    debugging "INFO: ${local_virtualenv} -p python${pyver} --system-site-packages ${venv} > /dev/null 2>&1"
    if ! (${local_virtualenv} -p python${pyver} --system-site-packages ${venv} > /dev/null 2>&1); then
        assert "Creation of virtual environment failed"
    fi
    debugging "venv_python: ${venv_python}"
    if [ ! -r ${venv_python} ]; then assert "failed to initialize virtual environment"; fi
}

initialize_basedir() {
    debugging "Initializing: ${pf9_basedir}"
    if [[ -n "${init_flag}" ]]; then
	debugging "DELETEING Existing State Directories: ${pf9_state_dirs}"
        for dir in ${pf9_state_dirs}; do
	    if [ -d "${dir}" ]; then
		debugging "DELETING ${dir}"
	        rm -rf "${dir}"
	        if [ -d "${dir}" ]; then assert "failed to remove ${dir}"; fi
	    fi
        done
    fi
    for dir in ${pf9_state_dirs}; do
	debugging "Ensuring ${dir} Exist"
        if ! mkdir -p "${dir}" > /dev/null 2>&1; then assert "Failed to create directory: ${dir}"; fi
    done
    debugging "Ensuring ${log_file} Exist"
    if ! mkdir -p "${dir}" > /dev/null 2>&1; then assert "Failed to create directory: ${dir}"; fi
    if ! touch "${log_file}" > /dev/null 2>&1; then assert "failed to create log file: ${log_file}"; fi
}

setup_pf9_bash_profile() {
    debugging "Setting up pf9_bash_profile"
    if [ -f ~/.bashrc ]; then
	bash_config=$(realpath ~/.bashrc)
    elif [ -f ~/.bash_profile ]; then
	bash_config=$(realpath ~/.bash_profile)
    elif [ -f ~/.profile ]; then
	bash_config=$(realpath ~/.profile)
    else
	bash_config=$(realpath ~/.bashrc)
	if ! touch "${bash_config}" >> ${log_file} 2>&1; then
	    debugging "Failed to create ${bash_config}, BASH profile not setup"; fi
    fi
    debugging "Using $bash_config to source ${pf9_bash_profile}"

    debugging "Writing pf9_bash_profile to: ${pf9_bash_profile}"
    # Write pf9_bin=${pf9_bin} to the bash_profile as this needs variable expansion
    echo "pf9_bin=${pf9_bin}" > ${pf9_bash_profile}
    debugging "pf9_bin=$(dirname $(realpath .))"
    # Write the rest of the bash_profile.
    # This is done in 2 steps as only the first line needs variable expansion.
    # The rest of the file must be written with variable test intact.
    cat <<'EOT' >> ${pf9_bash_profile}
if [[ -d "${pf9_bin}" ]]; then
    if ! echo "$PATH" | grep -q "${pf9_bin}"; then
	export PATH="${pf9_bin}:$PATH"
    fi
fi

EOT

    if [ -s ${pf9_bash_profile} ]; then
        debugging "pf9_bash_profile successfully written to: ${pf9_bash_profile}"
	if ! (grep -q "source ${pf9_bash_profile}" ${bash_config}); then
	    debugging "Adding 'source ${pf9_bash_profile}' to: ${bash_config}"
	    echo "source ${pf9_bash_profile}" >> ${bash_config}
	else
	    debugging "${bash_config} already configured to source ${pf9_bash_profile}"
	fi
    else
	assert "Failed to write pf9_bash_profile to: ${pf9_bash_profile}"
    fi
}

create_cli_config(){
    debugging "Creating Platform9 CLI Configuration"
    auth_retry=0
    max_auth_retry=3
    while (( ${auth_retry} < ${max_auth_retry} )); do
	(( auth_retry++ ))
	if [ $auth_retry -gt 1 ]; then
	    stdout_log "Attempt $auth_retry of ${max_auth_retry}:"; fi

    if [ ! -z "${PF9_MGMTURL}" ] && [ ! -z "${PF9_USER}" ] && [ ! -z "${PF9_PASS}" ] && [ ! -z "${PF9_REGION}" ] && [ ! -z "${PF9_TENANT}" ]; then
        eval "${cli_exec}" config create --du_url ${PF9_MGMTURL} --os_username ${PF9_USER} --os_password ${PF9_PASS} --os_region ${PF9_REGION} --os_tenant ${PF9_TENANT}
    else
        echo ""
        stdout_log "Please provide your Platform9 Credentials"
        eval "${cli_exec}" config create
    fi

	if (${cli_exec} config validate); then
        stdout_log "Successfully validated the Platform9 account details"
	    break
	else
	    debugging "Config creation failed"
	    if (( $auth_retry == $max_auth_retry )); then
                echo ""
                stdout_log "Max Authentication Attempts Reached."
		stdout_log "You can retry entering your credentials with:"
		echo "    ${cli_exec} config create --help"
		eval "${cli_exec}" config create --help
                echo ""
                echo ""
                echo ""
	    fi
	fi
    done
}

validate_platform() {
  # check if running CentOS 7, Ubuntu 16.04, or Ubuntu 18.04
  source /etc/os-release
  if [[ "$ID" == "ubuntu" ]]; then
     platform="ubuntu"
     if [[ "$VERSION_ID" != "18.04" ]] && [[ "$VERSION_ID" != "16.04" ]]; then
         stdout_log "Unsupported Ubuntu version"
         exit 99
     fi
  elif [[ "$ID" == "centos" ]]; then
     platform="centos"
     if [[ "$VERSION_ID" != "7" ]]; then
         stdout_log "Unsupported CentOS version"
         exit 99
     fi
  else
     stdout_log "Unsupported Linux distribution"
     exit 99
  fi
}

install_prereqs() {
    stdout_log "Validating and installing package dependencies"
    source /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        # add ansible repository
        sudo apt-get update -y > /dev/null 2>&1
        if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to update apt repository - here's the last 10 lines of the log:\n"
                tail -10 ${log_file}; exit 1
        fi

        for pkg in haveged sshpass; do
            dpkg-query -f '${binary:Package}\n' -W | grep ^${pkg}$ > /dev/null 2>&1
            if [ $? -ne 0 ]; then
                sudo apt-get -y install ${pkg} >> ${log_file} 2>&1
                if [ $? -ne 0 ]; then
                    echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
                    tail -10 ${log_file}; exit 1
                fi
            fi
        done
        # Install python3-distutils only for 18.04
        if [[ "$VERSION_ID" == "18.04" ]]; then
            sudo apt-get -y install python3-distutils >> ${log_file} 2>&1
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
                tail -10 ${log_file}; exit 1
            fi
        fi
    elif [[ "$ID" == "centos" ]]; then
        sudo rpm -Uvh https://download.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
        for pkg in git haveged sshpass; do
            sudo yum install -y ${pkg} >> ${log_file} 2>&1
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
                tail -10 ${log_file}; exit 1
            fi
        done
        sudo haveged
    else
        echo -e "\nERROR: Unsupported platform ${ID}-${VERSION_ID}."; exit 1
    fi
}

## main

# Set the path so double quotes don't use the litteral '~'
pf9_basedir=$(dirname ~/pf9/.)
log_file=${pf9_basedir}/log/cli_install.log
pf9_bin=${pf9_basedir}/bin
venv="${pf9_basedir}/pf9-venv"
pf9_state_dirs="${pf9_bin} ${venv} ${pf9_basedir}/db ${pf9_basedir}/log"

parse_args "$@"

# initialize installation directory
initialize_basedir

# Validate & install system packages
validate_platform
install_prereqs

debugging "CLFs: $*"

# Set global variables

if [ -z ${branch} ]; then
    branch=$(git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')
    if [ $? -ne 0 ]; then
	branch=master
    fi
fi
debugging "Setting environment variables to be passed to installers"

if [[ -z ${run_local} && -z ${dev_build} ]]; then
    cli_url="git+git://github.com/platform9/express-cli.git@${branch}#egg=express-cli"
elif [[ -n ${dev_build} ]]; then
    cli_url="-e .[test]"
elif [[ -n ${run_local} ]]; then
    cli_url="."
fi
debugging "branch: ${branch}"
debugging "cli_url: ${cli_url}"

pip_path=${pf9_basedir}/get_pip.py
venv_python="${venv}/bin/python"
venv_activate="${venv}/bin/activate"
pip_url="https://bootstrap.pypa.io/get-pip.py"
cli_entrypoint=$(dirname ${venv_python})/express
cli_exec=${pf9_bin}/pf9ctl
pf9_bash_profile=${pf9_bin}/pf9-bash-profile.sh
local_pip=$(dirname ~/.)/.local/bin/pip
local_virtualenv=$(dirname ~/.)/.local/bin/virtualenv

# configure python virtual environment
debugging "Configuring virtualenv"
if [ ! -f "${venv_activate}" ]; then
    init_venv_python
else
    stdout_log "INFO: using exising virtual environment"
fi

stdout_log "Upgrading pip"
if ! (${venv_python} -m pip install --upgrade --ignore-installed pip setuptools wheel >> ${log_file} 2>&1); then
    assert "Pip upgrade failed"; fi
debugging "pip install express-cli completed"

stdout_log "Installing Platform9 CLI"
if ! (${venv_python} -m pip install --upgrade --ignore-installed ${cli_url} >> ${log_file} 2>&1); then
    assert "Installation of Platform9 CLI Failed"; fi

if ! (${cli_entrypoint} --help >> ${log_file} 2>&1); then
    assert "Base Installation of Platform9 CLI Failed"; fi

if [ ! -f ${cli_exec} ]; then
    debugging "Creating Platform9 CLI symlink"
    if [ -L ${cli_exec} ]; then
        if ! (rm ${cli_exec} >> ${log_file} 2>&1); then
	        assert "Failed to remove existing symlink: ${cli_exec}"; fi
    fi
    if ! (ln -s ${cli_entrypoint} ${cli_exec} >> ${log_file} 2>&1); then
	    assert "Failed to create Platform9 CLI symlink: ${cli_exec}"; fi
else
    debugging "Platform9 CLI symlink already exist"
fi

# Create symlink in /usr/bin
if [ -L /usr/bin/pf9ctl ]; then
    if ! (sudo rm /usr/bin/pf9ctl >> ${log_file} 2>&1); then
        assert "Failed to remove existing symlink: ${cli_exec}"; fi
fi
if ! (sudo ln -s ${cli_entrypoint} /usr/bin/pf9ctl >> ${log_file} 2>&1); then
    assert "Failed to create Platform9 CLI symlink in /usr/bin"; fi

if ! (${cli_exec} --help >> ${log_file} 2>&1); then
    assert "Installation of Platform9 CLI Failed"; fi

# Setup pf9_bash_profile which creates a bash file that adds ~/pf9/bin to the users path and enables bash-completion
# An entry to source ~/pf9/bin/pf9_bash_profile is created in one of the following ~/.bashrc, ~/.bash_profile, ~/.profile
setup_pf9_bash_profile
if [[ ${bash_config} ]]; then
    eval source "${bash_config}"
fi
if ! [[ -n ${install_only} ]]; then
    # call cli config create which will prompt user to provide PF9 credentials.
    create_cli_config
fi
echo ""
stdout_log "Platform9 CLI installation completed successfully"
echo ""
echo "To start building a Kubernetes cluster you can execute:"
echo "        ${cli_exec} cluster --help"
echo ""
eval "${cli_exec}" cluster --help
