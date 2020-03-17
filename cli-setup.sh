#!/bin/bash

set -o pipefail

flag_testsetup=0
log=/tmp/pf9-cli-setup.log
cli_setup_dir=/opt/pf9/cli

write_out_log() {
    echo "$1" 2>&1 | tee -a ${log}
}

write_out_log_no_new_line() {
    echo -n "$1" 2>&1 | tee -a ${log}
}

install_prereqs() {
    write_out_log "Validating and installing package dependencies"
    if [ "${platform}" == "ubuntu" ]; then
        # add ansible repository
        dpkg-query -f '${binary:Package}\n' -W | grep ^ansible$ > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            sudo apt-add-repository -y ppa:ansible/ansible > /dev/null 2>&1
            sudo apt-get update> /dev/null 2>&1
            sudo apt-get -y install ansible >> ${log} 2>&1
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
                tail -10 ${log}; exit 1
            fi
        fi

        for pkg in jq bc; do
            dpkg-query -f '${binary:Package}\n' -W | grep ^${pkg}$ > /dev/null 2>&1
            if [ $? -ne 0 ]; then
                sudo apt-get -y install ${pkg} >> ${log} 2>&1
                if [ $? -ne 0 ]; then
                    echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
                    tail -10 ${log}; exit 1
                fi
            fi
        done
    else
        echo -e "\nERROR: Unsupported platform ${platform}. Please use an Ubuntu 16.04 platform"; exit 1
    fi
}

install_pip_prereqs() {
        ## upgrade pip
        write_out_log "Upgrading ${cli_setup_dir}/bin/pip to latest version"
        sudo ${cli_setup_dir}/bin/pip install --upgrade pip >> ${log} 2>&1
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to upgrade pip - here's the last 10 lines of the log:\n"
            tail -10 ${log}; exit 1
        fi

        ## install additional pip-based packages
        write_out_log "Installing dependencies from pypi in ${cli_setup_dir}"
        for pkg in openstacksdk; do
            sudo ${cli_setup_dir}/bin/pip install ${pkg} --ignore-installed >> ${log} 2>&1
            if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
            tail -10 ${log}; exit 1
            fi
        done

    # create log directory
    if [ ! -d /var/log/pf9 ]; then sudo mkdir -p /var/log/pf9; fi
}

validate_platform() {
  # check if running CentOS 7, Ubuntu 16.04, or Ubuntu 18.04
  if [ -r /etc/centos-release ]; then
    release=$(cat /etc/centos-release | cut -d ' ' -f 4)
    if [[ ! "${release}" == 7.* ]]; then
        write_out_log "Unsupported CentOS release: ${release}"
        exit 99
    fi
    platform="centos"
    host_os_info=$(cat /etc/centos-release)
  elif [ -r /etc/lsb-release ]; then
    release=$(cat /etc/lsb-release | grep ^DISTRIB_RELEASE= /etc/lsb-release | cut -d '=' -f2)
    if [[ ! "${release}" == 16.04* ]]; then
        write_out_log "Unsupported Ubuntu release: ${release}"
        exit 99
    fi
    platform="ubuntu"
    ubuntu_release=$(cat /etc/lsb-release | grep ^DISTRIB_RELEASE | cut -d = -f2)
    host_os_info="${platform} ${ubuntu_release}"
  else
    write_out_log "Unsupported platform"
    exit 99
  fi
}

ensure_py_pip_setup() {
    py3_exec=$(which python3)
    if [ $? -eq 0 ]; then
        use_py3=1
        py_exec=${py3_exec}
        write_out_log "Found python3 installation ${py_exec}. Installing CLI for python3 setup."
    else
        py2_exec=$(which python2)
        if [ $? -ne 0 ]; then
            # report no python error and quit
            write_out_log "Did not find python3 nor python2 on the host. Install either one of them and retry."
            exit 1
        fi
        py_exec=${py2_exec}
        write_out_log "Found python2 installation ${py_exec}. Installing CLI for python2 setup."
    fi

    #Install pip if not present
    if [ ${use_py3} -eq 1 ]; then
        #YUCK.. Need this hack for Ubuntu16.04
        if [ "${platform}" == "ubuntu" ]; then
            # python3-venv install fails on fresh ubuntu without an update
            sudo apt-get update > /dev/null
            sudo apt-get -y install python3-venv 2>&1 >> ${log}
        fi
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to install python3-venv - here's the last 10 lines of the log ${log}:\n"
            tail -10 ${log}; exit 1
        fi
        pip3_exec=$(which pip3)
        if [ $? -ne 0 ]; then
            curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
            sudo ${py3_exec} /tmp/get-pip.py 2>&1 >> ${log}
        fi
        pip3_exec=$(which pip3)
        sudo ${pip3_exec} install virtualenv 2>&1 >> ${log}
        venv_exec=$(which virtualenv)
    else
        pip2_exec=$(which pip)
        if [ $? -ne 0 ]; then
            curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
            sudo ${py2_exec} /tmp/get-pip.py 2>&1 >> ${log}
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to install pip - here's the last 10 lines of the log ${log}:\n"
                tail -10 ${log}
                exit 1
            fi
            venv_exec=$(which virtualenv)
            if [ $? -ne 0 ]; then
                sudo ${pip2_exec} install virtualenv 2>&1 >> ${log}
                if [ $? -ne 0 ]; then
                    echo -e "\nERROR: failed to install virtualenv - here's the last 10 lines of the log ${log}:\n"
                    tail -10 ${log}
                    exit 1
                fi
            fi
        fi
    fi
}

setup_venv() {
    sudo mkdir -p ${cli_setup_dir}
    if [ ${use_py3} -eq 1 ]; then
        sudo ${venv_exec} -p python3 --system-site-packages ${cli_setup_dir} 2>&1 >> ${log}
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to setup CLI env - here's the last 10 lines of the log ${log}:\n"
            tail -10 ${log}
            exit 1
        fi
    else
        sudo ${py2_exec} -m virtualenv ${cli_setup_dir} 2>&1 >> ${log}
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to setup CLI env - here's the last 10 lines of the log ${log}:\n"
            tail -10 ${log}
            exit 1
        fi
    fi
}

prompt_account_inputs() {
    if [ -z "${MGMTURL}" ]; then
        read -p "Platform9 account management URL [Example: https://example.platform9.io]: " MGMTURL
    fi
    if [[ ${MGMTURL} != https://* ]]; then
        MGMTURL=https://${MGMTURL}
        write_out_log "Platform9 account management URL should start with https://. Trying with ${MGMTURL}"
    fi
    if [ -z "${PF9_USER}" ]; then
        read -p "Platform9 account email: " PF9_USER
    fi
    if [ -z "${PASS}" ]; then
        read -sp "Platform9 user password: " PASS
        echo
    fi
    # Assume defaults for the region/project unless we get it from the env
    if [ -z "${PF9_PROJECT}" ]; then
        PROJECT=service
    else
        PROJECT=${PF9_PROJECT}
    fi
    if [ -z "${PF9_REGION}" ]; then
        REGION=RegionOne
    else
        REGION=${PF9_REGION}
    fi
    write_out_log "The setup is going to use the ${PROJECT} project under the ${REGION} region"
}

setup_express() {
    write_out_log "Installing the CLI"
    if [ ${flag_testsetup} -eq 1 ]; then
        # Dependencies are not well handled with the test pypi. Install explicityly first.
        # TODO: Explore if there is a better way to handle dependencies like below
        sudo ${cli_setup_dir}/bin/pip install click requests prettytable netifaces colorama urllib3 paramiko fabric invoke 2>&1 >> ${log}
        sudo ${cli_setup_dir}/bin/pip install --upgrade --index-url https://test.pypi.org/simple/ express-cli 2>&1 >> ${log}
    else
        sudo ${cli_setup_dir}/bin/pip install --upgrade express-cli 2>&1 >> ${log}
    fi

    if [ $? != '0' ]
    then
        write_out_log "CLI installation failed"
        echo -e "\nhere's the last 10 lines of the log ${log}:\n"
        tail -10 ${log}
        exit 1
    fi

    write_out_log "Initializing the CLI"
    ${cli_setup_dir}/bin/express init 2>&1 >> ${log}

    write_out_log "Configuring the CLI with your Platform9 account"
    attempt=1
    while [ $attempt -le 3 ]; do
        prompt_account_inputs
        echo "Running ${cli_setup_dir}/bin/express config create --config_name pf9-express ${configname} --du ${MGMTURL} --os_username ${PF9_USER} --os_password *** --os_region ${REGION} --os_tenant ${PROJECT}" >> ${log}
        ${cli_setup_dir}/bin/express config create --config_name pf9-express ${configname} --du ${MGMTURL} --os_username ${PF9_USER} --os_password ${PASS} --os_region ${REGION} --os_tenant ${PROJECT} 2>&1 >> ${log}
        write_out_log "Validating the provided Platform9 account details"
        ${cli_setup_dir}/bin/express config validate 2>&1 >> ${log}
        if [ $? -ne 0 ]; then
            write_out_log "Failed to validate the Platform9 account provided. Let's retry."
            attempt=$((attempt+1))
            continue
        else
            write_out_log "Successfully validated the Platform9 account details"
            break
        fi
    done
    if [ $attempt -eq 4 ]; then
        write_out_log "Failed validation on multiple attempts. Giving up."
        exit 1
    fi

    sudo ln -sf ${cli_setup_dir}/bin/express /usr/bin/express
    sudo ln -sf ${cli_setup_dir}/bin/express /usr/bin/pf9ctl
    write_out_log "CLI installation was successful."
    echo "Invoke it using 'pf9ctl' command. For cluster operations, usage help is below:"
    /usr/bin/pf9ctl cluster --help

}

while [ $# -gt 0 ]; do
    # Needs more error handling in case arg parsing fails
    case ${1} in
    -t|--test)
        flag_testsetup=1
    ;;
    --pf9_account_url)
        MGMTURL=${2}
    shift
    ;;
    --pf9_email)
        PF9_USER=${2}
    shift
    ;;
    --pf9_password)
        PASS=${2}
    shift
    ;;
    --pf9_region)
        REGION=${2}
    shift
    ;;
    --pf9_project)
        TENANT=${2}
    shift
    ;;
    -l|--log)
        log=${2}
        shift
    esac
    shift
done

echo >> ${log} 2>&1
write_out_log "####################################################################"
write_out_log "Start install of Platform9 CLI on $(date)"
write_out_log "Detailed output of the install is available at ${log}"
write_out_log "####################################################################"


validate_platform
install_prereqs
ensure_py_pip_setup
setup_venv

# All operations below occur inside the venv
install_pip_prereqs
setup_express

