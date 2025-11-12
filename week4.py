import csv
import os
import uuid
from datetime import datetime
from collections import defaultdict, namedtuple

DATA_FILE = "expenses.csv"
DateFmt = "%Y-%m-%d"  # ISO date format

Expense = namedtuple("Expense", ["id", "date", "amount", "category", "description"])

class ExpenseTracker:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file
        self.expenses = []  # list of Expense
        self._ensure_file()
        self.load()

    def _ensure_file(self):
        """Ensure CSV file exists with header."""
        if not os.path.exists(self.data_file):
            with open(self.data_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "date", "amount", "category", "description"])

    def add_expense(self, amount, category, date=None, description=""):
        """Add a new expense and save to file. date can be string 'YYYY-MM-DD' or None for today."""
        if date is None:
            date_obj = datetime.today()
        else:
            try:
                date_obj = datetime.strptime(date, DateFmt)
            except ValueError:
                raise ValueError(f"Date must be in YYYY-MM-DD format. Got: {date}")
        try:
            amt = float(amount)
        except ValueError:
            raise ValueError("Amount must be a number.")
        new = Expense(id=str(uuid.uuid4()), date=date_obj.strftime(DateFmt),
                      amount=f"{amt:.2f}", category=category.strip(), description=description.strip())
        self.expenses.append(new)
        self._append_to_file(new)
        return new

    def _append_to_file(self, expense):
        with open(self.data_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([expense.id, expense.date, expense.amount, expense.category, expense.description])

    def load(self):
        """Load expenses from CSV into memory."""
        self.expenses = []
        with open(self.data_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Basic validation and normalization
                try:
                    amt = float(r["amount"])
                except Exception:
                    continue
                date_str = r["date"]
                # Ensure date format
                try:
                    datetime.strptime(date_str, DateFmt)
                except Exception:
                    continue
                exp = Expense(id=r["id"], date=date_str, amount=f"{amt:.2f}",
                              category=r.get("category", "").strip(), description=r.get("description", "").strip())
                self.expenses.append(exp)

    def list_expenses(self, year=None, month=None, category=None, limit=None):
        """Return list of expenses optionally filtered by year, month (int), or category."""
        results = []
        for e in self.expenses:
            dt = datetime.strptime(e.date, DateFmt)
            if year is not None and dt.year != year:
                continue
            if month is not None and dt.month != month:
                continue
            if category is not None and e.category.lower() != category.lower():
                continue
            results.append(e)
        # sort by date descending
        results.sort(key=lambda x: x.date, reverse=True)
        if limit:
            return results[:limit]
        return results

    def monthly_report(self, year, month):
        """Return a dict: {category: {"amount": total, "count": n}} plus overall total."""
        totals = defaultdict(lambda: {"amount": 0.0, "count": 0})
        total_spent = 0.0
        for e in self.list_expenses(year=year, month=month):
            amt = float(e.amount)
            totals[e.category]["amount"] += amt
            totals[e.category]["count"] += 1
            total_spent += amt
        # Convert amounts to 2-decimal strings for display/export
        report = {cat: {"amount": round(vals["amount"], 2), "count": vals["count"]} for cat, vals in totals.items()}
        return {"year": year, "month": month, "categories": report, "total_spent": round(total_spent, 2)}

    def export_report_csv(self, report, filename):
        """Export monthly report (from monthly_report) to CSV."""
        rows = [["Category", "Total Amount", "Count"]]
        for cat, vals in report["categories"].items():
            rows.append([cat, f"{vals['amount']:.2f}", str(vals["count"])])
        rows.append([])
        rows.append(["Total", f"{report['total_spent']:.2f}", ""])
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return filename

    def export_report_text(self, report, filename):
        """Export monthly report to a human-readable text file."""
        month_name = datetime(report["year"], report["month"], 1).strftime("%B %Y")
        lines = [
            f"Monthly Report - {month_name}",
            "="*40,
            ""
        ]
        if not report["categories"]:
            lines.append("No expenses recorded for this month.")
        else:
            for cat, vals in sorted(report["categories"].items(), key=lambda x: -x[1]["amount"]):
                lines.append(f"{cat}: ₹{vals['amount']:.2f} ({vals['count']} items)")
            lines.append("")
            lines.append(f"Total Spent: ₹{report['total_spent']:.2f}")
        content = "\n".join(lines)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return filename

    def delete_expense(self, expense_id):
        """Delete expense by id. Will rewrite file."""
        before = len(self.expenses)
        self.expenses = [e for e in self.expenses if e.id != expense_id]
        after = len(self.expenses)
        if before == after:
            return False
        # rewrite CSV
        with open(self.data_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "amount", "category", "description"])
            for e in self.expenses:
                writer.writerow([e.id, e.date, e.amount, e.category, e.description])
        return True


def prompt_date(prompt_msg="Enter date (YYYY-MM-DD) [default today]: "):
    entry = input(prompt_msg).strip()
    if entry == "":
        return None
    # validate
    try:
        datetime.strptime(entry, DateFmt)
        return entry
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return prompt_date(prompt_msg)


def main_menu():
    tracker = ExpenseTracker()
    while True:
        print("\n=== Personal Finance Tracker ===")
        print("1. Add expense")
        print("2. List recent expenses")
        print("3. Show monthly report")
        print("4. Export monthly report (CSV or TXT)")
        print("5. Delete an expense")
        print("6. Exit")
        choice = input("Choose (1-6): ").strip()
        if choice == "1":
            amt = input("Amount (numbers only): ").strip()
            cat = input("Category (e.g., Food, Transport, Bills): ").strip() or "Uncategorized"
            date = prompt_date()
            desc = input("Description (optional): ").strip()
            try:
                new = tracker.add_expense(amount=amt, category=cat, date=date, description=desc)
                print(f"Added: {new.date} | {new.category} | ₹{new.amount} | {new.description}")
            except Exception as e:
                print("Error adding expense:", e)
        elif choice == "2":
            n = input("How many recent items to show? (enter for 10): ").strip()
            try:
                limit = int(n) if n else 10
            except ValueError:
                limit = 10
            items = tracker.list_expenses(limit=limit)
            if not items:
                print("No expenses recorded yet.")
            else:
                print("\nRecent expenses:")
                for e in items:
                    print(f"[{e.id[:8]}] {e.date} | {e.category} | ₹{e.amount} | {e.description}")
        elif choice == "3":
            y = input("Enter year (YYYY) [default this year]: ").strip()
            m = input("Enter month (1-12) [default this month]: ").strip()
            try:
                year = int(y) if y else datetime.today().year
                month = int(m) if m else datetime.today().month
                report = tracker.monthly_report(year, month)
                mn = datetime(year, month, 1).strftime("%B %Y")
                print(f"\nReport for {mn}")
                print("-"*40)
                if not report["categories"]:
                    print("No expenses for this month.")
                else:
                    for cat, vals in sorted(report["categories"].items(), key=lambda x: -x[1]["amount"]):
                        print(f"{cat:20} ₹{vals['amount']:10.2f}   ({vals['count']} items)")
                    print("-"*40)
                    print(f"Total Spent: ₹{report['total_spent']:.2f}")
            except Exception as e:
                print("Invalid input:", e)
        elif choice == "4":
            y = input("Year (YYYY) [default this year]: ").strip()
            m = input("Month (1-12) [default this month]: ").strip()
            try:
                year = int(y) if y else datetime.today().year
                month = int(m) if m else datetime.today().month
                report = tracker.monthly_report(year, month)
                if not report["categories"]:
                    print("No expenses for that month; nothing to export.")
                    continue
                fmt = input("Export format (csv/txt) [csv]: ").strip().lower() or "csv"
                safe_month = f"{year}-{month:02d}"
                if fmt == "csv":
                    filename = f"report_{safe_month}.csv"
                    tracker.export_report_csv(report, filename)
                    print(f"Report exported to {filename}")
                else:
                    filename = f"report_{safe_month}.txt"
                    tracker.export_report_text(report, filename)
                    print(f"Report exported to {filename}")
            except Exception as e:
                print("Error exporting report:", e)
        elif choice == "5":
            eid = input("Enter expense id (first 8 chars shown in lists): ").strip()
            if not eid:
                print("No id entered.")
                continue
            # Try to find full id
            matches = [e for e in tracker.expenses if e.id.startswith(eid)]
            if not matches:
                print("No expense found with that id prefix.")
                continue
            if len(matches) > 1:
                print("Multiple matches found. Be more specific.")
                for e in matches:
                    print(f"{e.id} | {e.date} | {e.category} | ₹{e.amount} | {e.description}")
                continue
            confirm = input(f"Delete expense {matches[0].id[:8]} {matches[0].date} {matches[0].category} ₹{matches[0].amount}? (y/N): ").strip().lower()
            if confirm == "y":
                ok = tracker.delete_expense(matches[0].id)
                if ok:
                    print("Deleted.")
                else:
                    print("Failed to delete.")
            else:
                print("Aborted.")
        elif choice == "6":
            print("Bye.")
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main_menu()
