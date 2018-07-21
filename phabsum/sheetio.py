import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SheetIO(object):
    def __init__(self,secret_file,sheet_url,summary_sheet_index=0,data_sheet_index=1):
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(secret_file, scope)
        self.g_connection = gspread.authorize(credentials)
        self.sheet = self.g_connection.open_by_url(sheet_url)
        self.worksheet_summary = self.sheet.get_worksheet(summary_sheet_index)
        self.worksheet_data = self.sheet.get_worksheet(data_sheet_index)

    def add_log_summary(self, date, name, activities):
        self.worksheet_summary.append_row([date,name,activities])
    
    def add_log_data(self, datetime, name, activity, ticket_url):
        self.worksheet_data.append_row([datetime,name,activity, ticket_url])

    