
import requests

class SlackIO(object):
    def __init__(self, webhook):
        self.webhook = webhook
    
    def report(self, date, authors):
        attachments = list()
        for _,author in authors.iteritems():
            attachments.append(
                {
                    "title":author["name"],
                    "text":author["transactions_summary_slack"],
                    "mrkdwn_in": ["text"]
                }
            )


        formatted_message = {
            "text": "Daily Logs Report %s" %(date.strftime("%d/%m/%Y")),
            "attachments": attachments
        }
        return requests.post(self.webhook,json=formatted_message)