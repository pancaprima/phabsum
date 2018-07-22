
import requests
import time
from .sheetio import SheetIO
from .slackio import SlackIO
import traceback

class Phab(object):
    def __init__(self, url, token, gcred=None, gsheet_url=None, slack_hook=None):
        self.url = url if url[len(url)-1] == '/' else '%s/' % (url)
        self.token = token
        self.gsheet = SheetIO(gcred, gsheet_url) if not gcred is None and not gsheet_url is None else None
        self.slack = SlackIO(slack_hook) if not slack_hook is None else None
        self.transaction_type_catch_list = ["core:columns","core:comment","reassign"]

    def compile(self, project, date):
        try :
            epoch = int(time.mktime(time.strptime(date.strftime("%Y %m %d 00:00"),"%Y %m %d %H:%M")))
            maniphests = self.load_maniphests(project, epoch)
            if len(maniphests) > 0 :
                maniphests_dict = self.transform_maniphests_into_dict(maniphests)
                transactions = self.load_transactions(maniphests)
                authors_maniphests = self.transform_author_based_maniphests(maniphests_dict, transactions, epoch)
                self.report(authors_maniphests, date)
                print('Yeay, Summarized!')
            else :
                print("there is no activity today :(")
        except Exception as e:
            traceback.print_exc()
            print "FAILED to summarize!"

    def report(self, summary, date):
        print('recording/reporting...')
        send_gsheet = True if not self.gsheet is None else False
        send_slack  = True if not self.slack  is None else False
        for _,author in summary.iteritems():
            for transaction in author["transactions"]:
                date_time = time.strftime('%Y/%m/%d %H:%M', time.localtime(float(transaction["dateCreated"])))
                if send_gsheet : self.gsheet.add_log_data(date_time, author["name"], transaction["message"], self.ticket_url(transaction['taskID']))
                author["transactions_summary"] = transaction["formatted_message"] if author["transactions_summary"] == "" else '%s\n%s' % (author["transactions_summary"],transaction["formatted_message"])
                author["transactions_summary_slack"] = transaction["slack_message"] if author["transactions_summary_slack"] == "" else '%s\n%s' % (author["transactions_summary_slack"],transaction["slack_message"])
            if send_gsheet : self.gsheet.add_log_summary(date.strftime("%Y/%m/%d"),author["name"],author["transactions_summary"])
        if send_slack : self.slack.report(date,summary)
    
    def ticket_url(self, ticket_id):
        return '%sT%s' % (self.url,ticket_id)
    
    def load_author_name(self, authorPHID):
        body = {
            "api.token":self.token,
            "phids[0]":authorPHID 
        }
        r_author = requests.post(self.url+"api/phid.query", data=body).json()
        return r_author['result'][authorPHID]["fullName"]

    def load_maniphests(self, project, epoch_time):
        body = {
            "api.token":self.token,
            "constraints[projects][0]":project,
            "constraints[modifiedStart]":epoch_time,
            "attachments[columns]":1,
            "order[1]":"-updated",
            "order[0]":"id"
        }
        print('loading updated tasks today...')
        self.maniphests = requests.post(self.url+"api/maniphest.search", data=body).json()["result"]["data"]
        return self.maniphests

    def load_transactions(self, maniphests):
        body_task_transaction = {
            "api.token":self.token
        }
        for x in range(0,len(maniphests)) :
            body_task_transaction["ids[%s]" % (x)] = maniphests[x]["id"]
        print('loading tasks events...')
        return requests.post(self.url+"api/maniphest.gettasktransactions", data=body_task_transaction).json()["result"]

    def transform_author_based_maniphests(self, maniphests_dict, maniphest_transactions, epoch_time):
        print("compiling...")
        authors = dict()
        for _,transactions in maniphest_transactions.iteritems():
            for transaction in transactions :
                if self.should_be_reported(transaction, epoch_time)  :
                    if not transaction["authorPHID"] in authors :
                        authors[transaction["authorPHID"]] = {
                            "name" : self.load_author_name(transaction["authorPHID"]),
                            "transactions": list(),
                            "transactions_summary" : "",
                            "transactions_summary_slack" : ""
                        }
                    transaction["formatted_message"],transaction["message"],transaction["slack_message"] = self.generate_transaction_message(maniphests_dict,transaction)
                    authors[transaction["authorPHID"]]["transactions"].append(transaction)
                    authors[transaction["authorPHID"]]["transactions"] = self.bubble_sort(authors[transaction["authorPHID"]]["transactions"])
        return authors

    def transform_maniphests_into_dict(self, maniphests):
        maniphests_dict = dict()
        for x in range(0,len(maniphests)) :
            maniphests_dict[str(maniphests[x]["id"])] = maniphests[x]
        return maniphests_dict

    def generate_transaction_message(self, maniphests,transaction):
        message = ""
        slack_message = ""
        task_title = maniphests[transaction['taskID']]["fields"]["name"]
        transaction_time = time.strftime('%H:%M', time.localtime(float(transaction["dateCreated"])))
        if transaction['transactionType'] == self.transaction_type_catch_list[0]:
            previous_column = transaction["newValue"][0]["fromColumnPHIDs"].itervalues().next()
            new_column = transaction["newValue"][0]["columnPHID"]
            body_columns = {
                "api.token":self.token,
                "phids[0]": new_column,
                "phids[1]": previous_column
            }
            r_columns = requests.post(self.url+"api/phid.query", data=body_columns).json()
            message = "move [%s] from '%s' to '%s'" % (task_title,r_columns["result"][previous_column]["fullName"],r_columns["result"][new_column]["fullName"])
            slack_message = "move <%s|%s> from `%s` to `%s`" % (self.ticket_url(transaction['taskID']),task_title,r_columns["result"][previous_column]["fullName"],r_columns["result"][new_column]["fullName"])
        elif transaction['transactionType'] == self.transaction_type_catch_list[1]:
            message = "commented '%s' at [%s]" % (transaction["comments"],task_title)
            slack_message = "commented `%s` at <%s|%s>" % (transaction["comments"],self.ticket_url(transaction['taskID']),task_title) if len(transaction["comments"]) < 50 else "commented ```%s``` at <%s|%s>" % (transaction["comments"],self.ticket_url(transaction['taskID']),task_title)
        elif transaction['transactionType'] == self.transaction_type_catch_list[2]:
            message = 'claimed [%s]' % (task_title)
            slack_message = 'claimed <%s|%s>' % (self.ticket_url(transaction['taskID']),task_title)
        return '%s - %s' % (transaction_time,message), message, '%s - %s' % (transaction_time,slack_message)

    def should_be_reported(self, transaction, epoch):
        if int(transaction["dateCreated"]) > epoch and transaction["transactionType"] in self.transaction_type_catch_list :
            if transaction['transactionType'] == self.transaction_type_catch_list[0] :
                if len(transaction["newValue"][0]["fromColumnPHIDs"]) == 0:
                    return False
                elif transaction["newValue"][0]["fromColumnPHIDs"].itervalues().next() == transaction["newValue"][0]["columnPHID"]:
                    return False
            elif transaction['transactionType'] == self.transaction_type_catch_list[2] :
                transaction["authorPHID"] = transaction["newValue"]
            return True
        return False

    def bubble_sort(self, transactions):
        for passnum in range(len(transactions)-1,0,-1):
            for i in range(passnum):
                if int(transactions[i]["dateCreated"]) > int(transactions[i+1]["dateCreated"]):
                    temp = transactions[i]
                    transactions[i] = transactions[i+1]
                    transactions[i+1] = temp
        return transactions