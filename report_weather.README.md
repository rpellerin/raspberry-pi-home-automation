# Setup

1. Create a Google Spreadsheet, give the main sheet the title "Raw data".
1. From that Google Spreadsheet, create a linked Google App Script, whose `Code.gs` file must contain:

   ```javascript
   const sheetId = "ABC"; // Spreadsheet id, replace with yours

   const MAX_ROW_NUMBER = 39500;

   function getShouldSendEmails() {
     const sheet =
       SpreadsheetApp.openById(sheetId).getSheetByName("Door status");
     return sheet.getRange("F1").getValue();
   }

   function doGet(e) {
     const result = JSON.stringify(e); // assume success

     if (e.parameter == undefined || Object.keys(e.parameter).length === 0) {
       result = "no params given";
     } else {
       const rowData = [];
       for (var param in e.parameter) {
         Logger.log("In for loop, param=" + param);
         const value = e.parameter[param];
         switch (param) {
           case "datetime":
             rowData[1] = value;
             break;
           case "temperature":
             rowData[2] = value;
             break;
           case "humidity":
             rowData[3] = value;
             break;
           case "pressure":
             rowData[4] = value;
             break;
           case "door_status":
             rowData[5] = value;
             break;
           case "get_should_send_emails":
             result = getShouldSendEmails();
             return ContentService.createTextOutput(result);
           default:
             result = "failed";
             return ContentService.createTextOutput(result);
         }
       }
       rowData[0] = new Date();
       Logger.log(JSON.stringify(rowData));

       const sheet =
         SpreadsheetApp.openById(sheetId).getSheetByName("Raw data");

       while (sheet.getLastRow() >= MAX_ROW_NUMBER) {
         sheet.deleteRow(2); // Deletes the second row (the one below the headers)
       }

       const newRow = sheet.getLastRow() + 1;

       // Write new row to spreadsheet
       var newRange = sheet.getRange(newRow, 1, 1, rowData.length);
       newRange.setValues([rowData]);
     }

     return ContentService.createTextOutput(result);
   }
   ```

1. Deploy your script, copy the URL
1. Make sure it works locally by invoking:

   ```bash
   curl -L https://script.google.com/macros/s/XYZ/exec\?temperature\=20\&humidity\=50

   ```

1. On the Raspberry Pi, close this repo, install redis and set up the Python env from the root of this repo:

   ```bash
   sudo apt install redis-server
   python3 -m venv .env
   source .env/bin/activate
   pip3 install -r requirements.txt

   ```

1. In `weatherstation.py`, change the URL for your valid Google Script URL.
1. Run `sudo raspi-config`, in `3 Interface Options`, enable `I2C`.
1. Create a cronjob: `*/3 * * * * /home/pi/raspberry-pi-home-automation/.env/bin/python /home/pi/raspberry-pi-home-automation/temperature/weatherstation.py`
