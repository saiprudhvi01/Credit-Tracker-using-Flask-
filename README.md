# Shop Credit Tracker

## The Problem

Ravi runs a small grocery shop in Hyderabad and gives goods on credit (khata) to about 80 regular customers. He currently tracks everything in a paper notebook, which causes several problems:

- **Forgetfulness**: He forgets who owes him how much, sometimes losing money completely
- **No proof**: Customers argue "I paid you last week!" but Ravi has no documentation
- **Awkward reminders**: Asking people to pay is uncomfortable, so he delays reminders and customers delay payments
- **No visibility**: At month-end, he doesn't know how much money is stuck with customers

**Target users**: Small shop owners like Ravi who need a simple way to track customer credits and send payment reminders.

## What I Built

A web application that solves Ravi's core problems:

1. **Customer Management**: Add and manage customers with name, phone, and email
2. **Credit Tracking**: Record credits (goods given on credit) and payments received
3. **Dashboard**: Shows total customers, total pending amount, and recent transactions
4. **Payment Reminders**: Send automated email reminders to customers via Gmail integration
5. **Customer Detail View**: See full transaction history and pending balance for each customer
6. **Login System**: Simple username/password authentication to keep Ravi's data private

### What I Deliberately Left Out

- **SMS reminders**: Could be useful but adds complexity and cost
- **Reporting/analytics**: Monthly reports, charts, and trends are nice-to-have but not essential
- **Multi-user support**: Single shop owner is the target user
- **Payment processing**: Recording payments is enough; actual payment gateway integration is overkill
- **Mobile app**: Web app works on mobile browsers, which is sufficient

## Assumptions and Key Product Decisions

1. **Simple English**: Ravi reads simple English, so the UI uses straightforward language
2. **Mobile-first**: Ravi uses a smartphone, so the UI is optimized for phone-sized screens
3. **Fast data entry**: Adding a transaction takes seconds while a customer is at the counter
4. **Email is optional**: Not all customers have email, so reminders only work for those who do
5. **Single user**: One shop owner per installation - no multi-tenant complexity
6. **Local deployment**: Runs on Ravi's computer, no hosting needed

## Tech Stack and Why I Chose It

- **Backend**: Flask (Python)
  - Simple, lightweight, perfect for small applications
  - Easy to understand and modify
  - Built-in session management for login

- **Database**: SQLite
  - No separate database server needed
  - File-based, easy to backup
  - Sufficient for 80 customers and their transactions

- **Frontend**: Tailwind CSS (via CDN)
  - Mobile-responsive out of the box
  - Clean, modern UI without writing custom CSS
  - Fast development with utility classes

- **Email**: Gmail API with OAuth
  - Free, reliable email delivery
  - OAuth keeps credentials secure
  - Ravi likely already has a Gmail account

## How to Run Locally

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Step-by-Step Setup (under 10 minutes)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Gmail credentials**
   - Go to Google Cloud Console
   - Create a project and enable Gmail API
   - Create OAuth 2.0 credentials (Web application)
   - Add `http://localhost:5000/oauth2callback` to authorized redirect URIs
   - Download credentials JSON and save as `credentials.json` in the project folder

3. **Seed sample data (optional)**
   ```bash
   python seed_data.py
   ```
   This creates a demo user: username `ravi`, password `ravi123`

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   - Go to `http://localhost:5000`
   - Login with `ravi` / `ravi123` (if you seeded data)
   - Or create a new account by registering (you'll need to add a registration route or manually insert into database)

6. **Connect Gmail (for reminders)**
   - Click "Gmail Setup" in the nav
   - Click "Connect Gmail"
   - Authorize with your Google account

## What I Would Build Next With One More Week

1. **Registration page**: Allow new users to sign up without manual database insertion
2. **Edit/Delete**: Allow editing customer details and deleting incorrect transactions
3. **Monthly report**: Simple summary of credits and payments per month
4. **Bulk reminders**: Send reminders to all customers with pending amounts
5. **Search**: Quick search for customers by name or phone
6. **Export**: Download customer list or transaction history as CSV

## Time Spent

Approximately 4-5 hours of development time.
