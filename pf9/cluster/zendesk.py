import requests
import json
import re
import click
import subprocess
from progress.bar import Bar


class CreateTicket(object):

    def __init__(self, ctx, err_msg):


        self.du_url = ctx.params['du_url']
        self.default_email = ctx.params['du_username']
        self.tenant = ctx.params['du_tenant']
        self.message = err_msg

    def check_ticket(self):
        regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
        answer = input('\nDo you want to create a support ticket?'
                       + '\n' + 'yes or no' + '\n')
        if answer.lower() == 'yes' or answer.lower() == 'y':
            click.secho('Got the answer as: {}'.format(answer),
                        fg='green')
            click.secho('The following email address will be used as the address for communitaion in the ticket: {}'.format(self.default_email),
                        fg='green')
            email_option = \
                input('\nDo you want to change the email address for communication'
                       + '\n' + 'yes or no' + '\n')
            if email_option.lower() == 'yes' or email_option.lower() \
                == 'y':
                count = 0
                while count < 3:
                    email = input('Enter new email address: ')
                    if re.search(regex, email):
                        click.secho('Email is valid creating a ticket with this email address'
                                    , fg='green')
                        break
                    else:
                        click.secho('Invalid Email Address. Please try again'
                                    , fg='red')
                        count += 1
                if not re.search(regex, email):
                    click.secho('''Attempts exceeded!!\nCreating a support ticket with correspondence email: <{}> and management plane: {}'''.format(self.default_email,
                                self.du_url), fg='red')
            else:
                email = self.default_email
                click.secho('Creating a support ticket now with correspondence email: <{}> and management plane: {}'.format(email,
                            self.du_url), fg='green')
            ticket_id = self.create_ticket(email)
            self.upload_logs(ticket_id)
        else:
            exit()

    def upload_logs(self,ticket_id):

        path = str(self.message)
        filename = path.replace("Code: 4, output log: ","")
        S3_location = "http://uploads.platform9.com.s3-us-west-1.amazonaws.com/"+str(ticket_id)
        try:
#            f = open(filename)
            with Bar('Uploading', max=100) as bar:
                for i in range(100):
                    cmd = subprocess.run(["curl", "-T", filename, S3_location])
                    bar.next()
            click.secho("\n Uploading the log file {} to {}".format(filename,S3_location),
                        fg="green")
        except Exception as e:
            click.secho("File uploading failed with error {}".format(e.message))


    def create_ticket(self, email):
        cloud_name = self.du_url.replace('https://', '')
        tenant_name = self.tenant
        index = email.index('@')
        user_name = email[:index]
#        error_msg = ''
#        error_msg = self.message

#      click.secho("Ticket Created",fg = "green")

        url = 'https://cs.pf9.us/support/submit'

        payload = [
            {'name': 'requester_name', 'value': user_name},
            {'name': 'requester_email', 'value': email},
            {'name': 'cloud', 'value': cloud_name},
            {'name': 'region', 'value': tenant_name},
            {'name': 'cluster', 'value': ''},
            {'name': 'severity', 'value': 'product_inquiry/question'},
            {'name': 'business_impact', 'value': 'limited'},
            {'name': 'users_affected', 'value': 'no_users__n/a_'},
            {'name': 'component',
             'value': {'value': 'end_user-component-other',
             'name': 'Other', 'groupName': 'Other'}},
            {'name': 'component-other', 'value': ''},
            {'name': 'subject', 'value': 'pf9ctl prep-node is failing'},
            {'name': 'description', 'value': 'Encountered an error while preparing the provided nodes as Kubernetes nodes\nlog files are uploaded on: http://uploads.platform9.com.s3-us-west-1.amazonaws.com/<ticket_number>'},
            {'name': 'ccs', 'value': ''},
            ]

        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        ticket_id = json.loads(response.text)
        ticket_id = ticket_id['audit']['ticket_id']
        if response.status_code != 201:
            click.secho('Ticket creation failed with error {}'.format(response.status_code),
                        fg='red')
        else:

            click.secho('\nTicket with id {} created successfully'.format(ticket_id),
                        fg='green')
            click.secho('\nDetails has been sent to <{}> \nOne of the members of Platform9 Support Team will reach out to you shortly.'.format(email),
                        fg='green')
            return ticket_id
