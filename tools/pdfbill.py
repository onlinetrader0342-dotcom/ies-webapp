"""pdfbill.py — Bill ka PDF banao (print/customer ke liye)."""
import os
from fpdf import FPDF
from tools.db import connect
from tools import billing

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(os.path.dirname(HERE), "bills")
os.makedirs(OUTDIR, exist_ok=True)


class BillPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, "Imran Electric Store", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, "CNG Adda, Mandian, Abbottabad | 0321-9807144",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 10, "Shukriya! Dobara tashreef layein.", align="C")


def make_pdf(invoice_id):
    inv = billing.get_invoice(invoice_id)
    if not inv:
        return {"ok": False, "error": "bill nahi mila"}
    con = connect()
    cust = con.execute("SELECT name, phone FROM customers WHERE id=?",
                       (inv["customer_id"],)).fetchone()
    con.close()

    pdf = BillPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Bill #{inv['id']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Customer: {cust['name'] if cust else inv['customer_id']}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Date: {inv['at']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # items table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    for w, t in [(90, "Product"), (20, "Qty"), (30, "Rate"), (35, "Total")]:
        pdf.cell(w, 8, t, border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 11)
    for it in inv["items"]:
        name = it["name"][:40]
        pdf.cell(90, 8, name, border=1)
        pdf.cell(20, 8, str(it["qty"]), border=1, align="C")
        pdf.cell(30, 8, f"Rs {it['rate']}", border=1, align="R")
        pdf.cell(35, 8, f"Rs {it['rate'] * it['qty']}", border=1, align="R")
        pdf.ln()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(140, 9, "Total:", align="R", border=1)
    pdf.cell(35, 9, f"Rs {inv['total']}", align="R", border=1)
    pdf.ln(14)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {inv['at']} | By: {inv['by']}")

    path = os.path.join(OUTDIR, f"bill-{invoice_id}.pdf")
    pdf.output(path)
    return {"ok": True, "path": path}


if __name__ == "__main__":
    import sys
    r = make_pdf(int(sys.argv[1]))
    print(r)
