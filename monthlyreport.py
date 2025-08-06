import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import calendar
from fpdf import FPDF, XPos, YPos

# --- Configuration ---
# Base URL of the website
BASE_URL = "https://crm.dejavutechkenya.com/crm/main/"
MAIN_JOBCARDS_URL = BASE_URL + "mainjobcards.php"
JOB_CARD_DETAIL_URL = BASE_URL + "jBoard.php"

# --- PDF Report Class ---
class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, self.title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    def create_table(self, data, title):
        self.title = title
        self.add_page()
        
        # Define column widths (total width ~260mm for A4 landscape)
        col_widths = [15, 20, 30, 20, 25, 20, 20, 15, 30, 30, 35]
        headers = data.columns.tolist()
        
        # Header
        self.set_font('helvetica', 'B', 7)
        self.set_fill_color(200, 220, 255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, str(header), 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.ln()
        
        # Data rows
        self.set_font('helvetica', '', 7)
        fill_color_light = (245, 245, 245)
        fill_color_dark = (220, 220, 220)
        fill_toggle = False
        
        for index, row in data.iterrows():
            # Calculate row height based on longest content
            row_height = 0
            for i, col_name in enumerate(headers):
                cell_text = str(row[col_name])
                lines = self.multi_cell(col_widths[i], 5, cell_text, dry_run=True, output="LINES")
                num_lines = len(lines)
                if num_lines == 0:
                    num_lines = 1
                row_height = max(row_height, num_lines * 5)
            
            # Check for page break before drawing the row
            if self.get_y() + row_height > 195:
                self.add_page()
                self.set_font('helvetica', 'B', 7)
                self.set_fill_color(200, 220, 255)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 7, str(header), 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
                self.ln()
                self.set_font('helvetica', '', 7)

            # Draw the row background and border
            start_y = self.get_y()
            start_x = self.get_x()
            
            fill_color = fill_color_dark if fill_toggle else fill_color_light
            self.set_fill_color(*fill_color)
            self.rect(start_x, start_y, sum(col_widths), row_height, 'F')
            
            # Draw the horizontal border for the row
            self.line(start_x, start_y, start_x + sum(col_widths), start_y)
            self.line(start_x, start_y + row_height, start_x + sum(col_widths), start_y + row_height)
            
            # Draw the content of each cell
            for i, col_name in enumerate(headers):
                cell_text = str(row[col_name])
                self.set_xy(start_x, start_y)
                self.multi_cell(col_widths[i], 5, cell_text, border=0, align='L', fill=False)
                start_x += col_widths[i]

            self.set_xy(self.l_margin, start_y + row_height) # Move to the next line
            fill_toggle = not fill_toggle

def create_pdf_report(df, filename, report_title):
    """Creates a PDF file from a pandas DataFrame."""
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.create_table(df, report_title)
    pdf.output(filename)


# --- Script Functions ---
def get_jobcard_details(jobcard_number, cookies):
    """Fetches and parses the detailed job card page."""
    try:
        response = requests.get(
            f"{JOB_CARD_DETAIL_URL}?jobcardNo={jobcard_number}", cookies=cookies
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        details = {}
        form = soup.find('form', {'name': 'equipment'})
        if form:
            details['cusName'] = form.find('input', {'name': 'cusName'}).get('value', '').strip()
            details['modelseq'] = form.find('input', {'name': 'modelseq'}).get('value', '').strip()
            details['serialNumber'] = form.find('input', {'name': 'serialNumber'}).get('value', '').strip()
            details['contact'] = form.find('input', {'name': 'mobileNumber'}).get('value', '').strip()
            details['equipment'] = form.find('input', {'name': 'equipment'}).get('value', '').strip()
            details['fault'] = form.find('textarea', {'name': 'fault'}).get_text(strip=True)
            details['workdone'] = form.find('textarea', {'name': 'workdone'}).get_text(strip=True)
            
            tech_label = form.find('label', string='TECHNICIAN ASSIGNED')
            if tech_label:
                tech_select = tech_label.find_next_sibling('select', {'name': 'technician'})
                if tech_select:
                    selected_option = tech_select.find('option', selected=True)
                    if selected_option:
                        details['technician'] = selected_option.get_text(strip=True)
                    else:
                        first_option = tech_select.find('option')
                        details['technician'] = first_option.get_text(strip=True) if first_option else ""
                else:
                    details['technician'] = ""
            else:
                details['technician'] = ""
        
        return details
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for job card {jobcard_number}: {e}")
        return None
    except AttributeError:
        print(f"Could not find all required fields on job card page {jobcard_number}.")
        return None

def main():
    """Main function to orchestrate the scraping process."""
    session_cookie = input("Please enter the value of your PHPSESSID cookie: ")
    cookies = {'PHPSESSID': session_cookie}

    while True:
        try:
            target_year = int(input("Enter the year for the report (e.g., 2025): "))
            if target_year < 1900:
                print("Please enter a valid year.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number for the year.")
    
    while True:
        try:
            target_month = int(input("Enter the month for the report (1-12, e.g., 7 for July): "))
            if 1 <= target_month <= 12:
                break
            else:
                print("Invalid input. Please enter a number between 1 and 12.")
        except ValueError:
            print("Invalid input. Please enter a number for the month.")
    
    print("Fetching the main job card list...")
    try:
        response = requests.get(MAIN_JOBCARDS_URL, cookies=cookies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while accessing the main job cards page: {e}")
        print("Please ensure your session cookie is correct and not expired.")
        return

    table = soup.find('table', {'id': 'dataTable'})
    if not table:
        print("Could not find the job cards table. The cookie may be invalid or expired.")
        return

    jobcard_data = []
    rows = table.find('tbody').find_all('tr')
    
    month_name = calendar.month_name[target_month]
    print(f"Found {len(rows)} job cards. Filtering for {month_name} {target_year}...")

    for i, row in enumerate(rows):
        cells = row.find_all('td')
        if len(cells) < 8:
            continue

        jobcard_date_str = cells[1].get_text(strip=True)
        jobcard_number = cells[2].get_text(strip=True)
        status = cells[6].get_text(strip=True)

        try:
            jobcard_date = datetime.strptime(jobcard_date_str, '%Y-%m-%d %H:%M')
        except ValueError:
            print(f"Warning: Could not parse date '{jobcard_date_str}'. Skipping this row.")
            continue

        if jobcard_date.month == target_month and jobcard_date.year == target_year:
            print(f"Processing job card: {jobcard_number} (Card {i+1}/{len(rows)})")
            
            details = get_jobcard_details(jobcard_number, cookies)
            
            if details:
                jobcard_info = {
                    'Status': status,
                    'Date': jobcard_date_str,
                    'Jobcard No': jobcard_number,
                    'Customer Name': details.get('cusName'),
                    'Contact': details.get('contact'),
                    'Equipment': details.get('equipment'),
                    'Model': details.get('modelseq'),
                    'Serial Number': details.get('serialNumber'),
                    'Technician Assigned': details.get('technician'),
                    'Fault': details.get('fault'),
                    'Work Done': details.get('workdone'),
                }
                jobcard_data.append(jobcard_info)

    if not jobcard_data:
        print(f"No job cards found for {month_name} {target_year}.")
        return

    print("Creating reports...")
    df = pd.DataFrame(jobcard_data)
    
    # Save to Excel
    excel_file_name = f"jobcards_{month_name}_{target_year}.xlsx"
    df.to_excel(excel_file_name, index=False)
    
    # Save to PDF
    pdf_file_name = f"jobcards_{month_name}_{target_year}.pdf"
    report_title = f"Job Card Report for {month_name} {target_year}"
    create_pdf_report(df, pdf_file_name, report_title)
    
    print(f"\nSuccessfully scraped and saved {len(jobcard_data)} job cards.")
    print(f"Excel file: {excel_file_name}")
    print(f"PDF file: {pdf_file_name}")

if __name__ == "__main__":
    main()