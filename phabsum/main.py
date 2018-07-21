import requests, datetime, time
from .sheetio import SheetIO
from .slackio import SlackIO

phab_token = "api-s4bokfglckcc4auoaj24ai6llixc"
date = datetime.date.today()
epoch = int(time.mktime(time.strptime(date.strftime("%Y %m %d 00:00"),"%Y %m %d %H:%M")))
transaction_type_catch_list = ["core:columns","core:comment","reassign"]
phab_url = "https://phab.tokopedia.com/"

def generate_transaction_message(maniphests,transaction):
    message = ""
    slack_message = ""
    task_title = maniphests[transaction['taskID']]["fields"]["name"]
    transaction_time = time.strftime('%H:%M', time.localtime(float(transaction["dateCreated"])))
    global transaction_type_catch_list
    if transaction['transactionType'] == transaction_type_catch_list[0]:
        previous_column = transaction["newValue"][0]["fromColumnPHIDs"].itervalues().next()
        new_column = transaction["newValue"][0]["columnPHID"]
        body_columns = {
            "api.token":phab_token,
            "phids[0]": new_column,
            "phids[1]": previous_column
        }
        r_columns = requests.post(phab_url+"api/phid.query", data=body_columns).json()
        message = "move [%s] from '%s' to '%s'" % (task_title,r_columns["result"][previous_column]["fullName"],r_columns["result"][new_column]["fullName"])
        slack_message = "move <%sT%s|%s> from `%s` to `%s`" % (phab_url,transaction['taskID'],task_title,r_columns["result"][previous_column]["fullName"],r_columns["result"][new_column]["fullName"])
    elif transaction['transactionType'] == transaction_type_catch_list[1]:
        message = "commented '%s' at [%s]" % (transaction["comments"],task_title)
        slack_message = "commented `%s` at <%s/T%s|%s>" % (transaction["comments"],phab_url,transaction['taskID'],task_title) if len(transaction["comments"] < 50) else "commented ```%s``` at <%sT%s|%s>" % (transaction["comments"],phab_url,transaction['taskID'],task_title)
    elif transaction['transactionType'] == transaction_type_catch_list[2]:
        message = 'claimed [%s]' % (task_title)
        slack_message = 'claimed <%sT%s|%s>' % (phab_url,transaction['taskID'],task_title)
    return '%s - %s' % (transaction_time,message), message, '%s - %s' % (transaction_time,slack_message)

def get_author_name(authorPHID):
    body_author = {
        "api.token":phab_token,
        "phids[0]":authorPHID 
    }
    r_author = requests.post(phab_url+"api/phid.query", data=body_author).json()
    return r_author['result'][authorPHID]["fullName"]

def should_be_reported(transaction):
    global transaction_type_catch_list, epoch
    if int(transaction["dateCreated"]) > epoch and transaction["transactionType"] in transaction_type_catch_list :
        if transaction['transactionType'] == transaction_type_catch_list[0] :
            if len(transaction["newValue"][0]["fromColumnPHIDs"]) == 0:
                return False
            elif transaction["newValue"][0]["fromColumnPHIDs"].itervalues().next() == transaction["newValue"][0]["columnPHID"]:
                return False
        elif transaction['transactionType'] == transaction_type_catch_list[2] :
            transaction["authorPHID"] = transaction["newValue"]
        return True
    return False

def bubble_sort(transactions):
    for passnum in range(len(transactions)-1,0,-1):
        for i in range(passnum):
            if int(transactions[i]["dateCreated"]) > int(transactions[i+1]["dateCreated"]):
                temp = transactions[i]
                transactions[i] = transactions[i+1]
                transactions[i+1] = temp
    return transactions

def main():
    body = {
        "api.token":phab_token,
        "constraints[projects][0]":"dexter_squad",
        "constraints[modifiedStart]":epoch,
        "attachments[columns]":1,
        "order[1]":"-updated",
        "order[0]":"id"
    }
    r_maniphest_search = requests.post(phab_url+"api/maniphest.search", data=body).json()
    if r_maniphest_search["error_code"] is None:
        maniphests = r_maniphest_search["result"]["data"]
        maniphests_dict = dict()
        body_task_transaction = {
            "api.token":phab_token
        }
        for x in range(0,len(maniphests)) :
            body_task_transaction["ids[%s]" % (x)] = maniphests[x]["id"]
            maniphests_dict[str(maniphests[x]["id"])] = maniphests[x]
        r_task_transaction = requests.post(phab_url+"api/maniphest.gettasktransactions", data=body_task_transaction).json()

        authors = dict()
        for _,transactions in r_task_transaction["result"].iteritems():
            for transaction in transactions:
                if should_be_reported(transaction)  :
                    if not transaction["authorPHID"] in authors :
                        authors[transaction["authorPHID"]] = {
                            "name" : get_author_name(transaction["authorPHID"]),
                            "transactions": list(),
                            "transactions_summary" : "",
                            "transactions_summary_slack" : ""
                        }
                    transaction["formatted_message"],transaction["message"],transaction["slack_message"] = generate_transaction_message(maniphests_dict,transaction)
                    authors[transaction["authorPHID"]]["transactions"].append(transaction)
                    authors[transaction["authorPHID"]]["transactions"] = bubble_sort(authors[transaction["authorPHID"]]["transactions"])
        
        gsheet = SheetIO('phabsum/creds.json','https://docs.google.com/spreadsheets/d/14r_7KPzIZ9l94NoEu5Nw0c6NT_1ArubHRvHNcnFEHJI/')
        slack = SlackIO("https://hooks.slack.com/services/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")
        for _,author in authors.iteritems():
            for transaction in author["transactions"]:
                date_time = time.strftime('%Y/%m/%d %H:%M', time.localtime(float(transaction["dateCreated"])))
                gsheet.add_log_data(date_time, author["name"], transaction["message"], phab_url+'T%s' % (transaction['taskID']))
                author["transactions_summary"] = transaction["formatted_message"] if author["transactions_summary"] == "" else '%s\n%s' % (author["transactions_summary"],transaction["formatted_message"])
                author["transactions_summary_slack"] = transaction["slack_message"] if author["transactions_summary_slack"] == "" else '%s\n%s' % (author["transactions_summary_slack"],transaction["slack_message"])
            gsheet.add_log_summary(date.strftime("%Y/%m/%d"),author["name"],author["transactions_summary"])
        slack.report(date,authors)

if __name__ == '__main__':
    main()