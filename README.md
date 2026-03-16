# GOSupportLog 📊

GOSupportLog is an automation tool designed to extract, analyze, and categorize technical support tickets from historical Telegram archives (HTML). It uses Artificial Intelligence (LLM) via Groq to transform informal conversations into structured Excel reports.

---

## 🚀 Technical Requirements

- Python 3.10+
- Install the dependencies by running:

```bash
  pip install -r requirements.txt
  # or individually:
  pip install pandas beautifulsoup4 openai python-dotenv openpyxl
  ```

## 🛠️ Installation and Configuration

1. **Clone the repository:**

```bash
   git clone https://github.com/xFrixonL/GOSupportLog.git
   cd GOSupportLog
   ```

2. **API Configuration:**

Create a file called `.env` in the project root and add your Groq key:

```env
   GROQ_API_KEY=your_groq_key_here
   ```

3. **Data Source:**

Place the exported Telegram file named `messages.html` in the folder Main script.

---

## 📈 Execution Flow

The script operates as follows:

1. **Extraction:** Loads the HTML file and normalizes the messages by day, identifying users and timestamps.

2. **Segmentation:** The user selects the range of days to process (e.g., 1-10) to manage API usage.

3. **Processing (AI):** Sends the chat snippet to the `llama-3.3-70b-versatile` model to extract the ticket logic (Category, Product, Resolution, and Status).

4. **Translation:** Dates detected in English are automatically converted to Spanish.

5. **Generation:** Creates an Excel file (.xlsx) with the processed day range.

---

## 📋 Report Structure

The generated file contains the following columns organized for analysis:

- Category (Ticket) / Subcategory
- Company (Report Issuer)
- Creation Date (Ticket)
- Product Name (Alert, Scan, or Kuntur)
- Status (Ticket) (Closed / Pending)
- Ticket ID
- Resolution (Final Technical Explanation)
- Resolution Date
- Resolved By (Technician in charge of closure)
- Priority (High, Medium, Low)
- Context (Details of the initial failure)

---

## 🔒 Security and Limits

- **Privacy:** The `.env` file and the `messages.html` source file must remain outside of version control. It is recommended to add them to `.gitignore`.

- **Rate Limits:** The script includes a system for retrying and automatically waiting in case of receiving a 429 error (Request Limit Reached).

---

## 🏃‍♂️ Quick Start

1. Export the Telegram chat and place it as `messages.html` in the project root.

2. Run the main script:

```bash
   python main.py
   ```
   
3. Select the range of days to process when prompted.

4. The report will be generated in Excel format.

---