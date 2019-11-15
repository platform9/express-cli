#!/bin/bash

set -xo pipefail

flag_testsetup=0
log=/tmp/pf9-cli-setup.log
cli_setup_dir=/opt/pf9/cli


install_prereqs() {
    echo -n "--> Validating package dependencies: "
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
            echo -n "${pkg} "
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
        echo -e "\nERROR: Unsupported platform ${platform}"; exit 1
    fi
}

install_pip_prereqs() {
        ## upgrade pip
        sudo ${cli_setup_dir}/bin/pip install --upgrade pip >> ${log} 2>&1
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to upgrade pip - here's the last 10 lines of the log:\n"
            tail -10 ${log}; exit 1
        fi

        ## install additional pip-based packages
        for pkg in shade; do
            echo -n "${pkg} "
            sudo ${cli_setup_dir}/bin/pip install ${pkg} --ignore-installed >> ${log} 2>&1
            if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to install ${pkg} - here's the last 10 lines of the log:\n"
            tail -10 ${log}; exit 1
            fi
        done
        echo

    # create log directory
    if [ ! -d /var/log/pf9 ]; then sudo mkdir -p /var/log/pf9; fi
}

validate_platform() {
  # check if running CentOS 7, Ubuntu 16.04, or Ubuntu 18.04
  if [ -r /etc/centos-release ]; then
    release=$(cat /etc/centos-release | cut -d ' ' -f 4)
    if [[ ! "${release}" == 7.* ]]; then assert "unsupported CentOS release: ${release}"; fi
    platform="centos"
    host_os_info=$(cat /etc/centos-release)
  elif [ -r /etc/lsb-release ]; then
    release=$(cat /etc/lsb-release | grep ^DISTRIB_RELEASE= /etc/lsb-release | cut -d '=' -f2)
    if [[ ! "${release}" == 16.04* ]] && [[ ! "${release}" == 18.04* ]]; then assert "unsupported Ubuntu release: ${release}"; fi
    platform="ubuntu"
    ubuntu_release=$(cat /etc/lsb-release | grep ^DISTRIB_RELEASE | cut -d = -f2)
    host_os_info="${platform} ${ubuntu_release}"
  else
    assert "unsupported platform"
  fi
}

ensure_py_pip_setup() {
    py3_exec=$(which python3)
    if [ $? -eq 0 ]; then
        use_py3=1
        py_exec=${py3_exec}
    else
        py2_exec=$(which python2)
        if [ $? -ne 0 ]; then
            # report no python error and quit
            echo "Error"
        fi
        py_exec=${py2_exec}
    fi

    #Install pip if not present
    if [ ${use_py3} -eq 1 ]; then
        #YUCK.. Need this hack for Ubuntu16.04
        if [ "${platform}" == "ubuntu" ]; then
            sudo apt-get update> /dev/null 2>&1 # python3-venv install fails on fresh ubuntu wihtout an update
            sudo apt-get -y install python3-venv
        fi
        if [ $? -ne 0 ]; then
            echo -e "\nERROR: failed to install python3-venv - here's the last 10 lines of the log:\n"
            tail -10 ${log}; exit 1
        fi
        pip3_exec=$(which pip3)
        if [ $? -ne 0 ]; then
            curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
            sudo ${py3_exec} /tmp/get-pip.py
        fi
        pip3_exec=$(which pip3)
        sudo ${pip3_exec} install virtualenv
        venv_exec=$(which virtualenv)
    else
        pip2_exec=$(which pip)
        if [ $? -ne 0 ]; then
            curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
            sudo ${py2_exec} /tmp/get-pip.py
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: failed to install pip.\n"
                exit 1
            fi
            venv_exec=$(which virtualenv)
            if [ $? -ne 0 ]; then
                sudo ${pip2_exec} install virtualenv
                if [ $? -ne 0 ]; then
                    echo -e "\nERROR: failed to install virtualenv.\n"
                    exit 1
                fi
            fi
        fi
    fi
}

setup_venv() {
    sudo mkdir -p ${cli_setup_dir}
    if [ ${use_py3} -eq 1 ]; then
        # TODO: Error handling
        sudo ${venv_exec} -p python3 --system-site-packages ${cli_setup_dir}
        #sudo ${py3_exec} -m venv ${cli_setup_dir} --system-site-packages
    else
        # TODO: Error handling
        sudo ${py2_exec} -m virtualenv ${cli_setup_dir}
    fi
}

setup_express() {
    echo "################################### Install express cli ########################################"
    if [ ${flag_testsetup} -eq 1 ]; then
        # Dependencies are not well handled with the test pypi. Install explicityly first.
        # TODO: Explore if there is a better way to handle dependencies like below
        sudo ${cli_setup_dir}/bin/pip install click requests prettytable
        sudo ${cli_setup_dir}/bin/pip install --index-url https://test.pypi.org/simple/ express-cli
    else
        sudo ${cli_setup_dir}/bin/pip install express-cli
    fi

    if [ $? != '0' ]
    then
        echo "express-cli installation failed"
        exit 1
    fi

    echo "############################ Initializing Platform9 Express CLI ################################"
    ${cli_setup_dir}/bin/express init

    echo "########################### Configuring the CLI to use your account #############################"
    read -p "Platform9 account FQDN: " DUFQDN
    read -p "Platform9 region: " REGION
    read -p "Platform9 username: " USER
    read -sp "Platform9 user password: " PASS
    read -p "Platform9 user tenant: " PROJECT
    ${cli_setup_dir}/bin/express config create --config_name pf9-express ${configname} --du ${DUFQDN} --os_username ${USER} --os_password ${PASS} --os_region ${REGION} --os_tenant ${PROJECT}
    sudo ln -s ${cli_setup_dir}/bin/express /usr/bin/express
}

while [ $# -gt 0 ]; do
    case ${1} in
    -t|--test)
        flag_testsetup=1
    ;;
    -l|--log)
        log=${2}
        shift
    esac
    shift
done

echo >> ${log} 2>&1
echo "######################################" >> ${log} 2>&1
echo "Start install of Platform9 CLI $(date)" >> ${log} 2>&1
#process_inputs
validate_platform
install_prereqs
ensure_py_pip_setup
setup_venv

# All operations below occur inside the venv
install_pip_prereqs
setup_express

