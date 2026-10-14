# Static demo data for seed_demo.py. Nothing here touches the database, so
# the file is safe to import and easy to edit.


# Build one bill template in a fixed shape. A small helper keeps the data
# below short and stops typos in key names.
def bill(seq, vendor, vendor_gstin, taxable, rate, interstate, status, days_ago):
    return {
        "seq": seq,
        "vendor": vendor,
        "vendor_gstin": vendor_gstin,
        "taxable": taxable,
        "rate": rate,
        "interstate": interstate,
        "status": status,
        "days_ago": days_ago,
    }


# interstate=True means IGST is charged, False means CGST + SGST.
# assigned_to decides which CA gets the client. A client with
# "status": "pending" is a signup request waiting for CA approval.
FIRM_SPECS = [
    {
        "key": "kulkarni",
        "name": "Kulkarni and Associates",
        "gstin": "27AAAFK1234A1Z5",
        "address": "12 FC Road, Pune, Maharashtra 411004",
        "invoice_prefix": "KUL",
        "ca": {"name": "Anil Kulkarni", "email_prefix": "partner.kulkarni", "membership_number": "123456"},
        "junior": {"name": "Neha Joshi", "email_prefix": "junior.kulkarni", "membership_number": "234567"},
        "clients": [
            {
                "business_name": "Sharma Traders", "owner_name": "Ramesh Sharma",
                "email_prefix": "sharma.traders", "gstin": "27BBBPS2222D1Z6",
                "mobile": "9800000001", "address": "Shop 4, Laxmi Road, Pune",
                "assigned_to": "junior",
                "bills": [
                    bill(1, "Om Paper Mart", "27AAACO1111K1Z7", 10000, 18, False, "uploaded", 1),
                    bill(2, "Ganesh Stationery Supplies", "27AABCS4444N1Z1", 25000, 12, False, "pending_review", 3),
                ],
            },
            {
                "business_name": "Patil Stationers", "owner_name": "Sunita Patil",
                "email_prefix": "patil.stationers", "gstin": "27CCCPT3333E1Z8",
                "mobile": "9800000002", "address": "Near Bus Stand, Satara",
                "assigned_to": "junior",
                "bills": [
                    bill(3, "Vishal Printing Works", "29AABCV2222L1Z4", 42000, 18, True, "approved", 9),
                    bill(4, "Sai Trading Co", "24AAECR3333M1Z9", 8000, 5, True, "rejected", 6),
                ],
            },
            {
                "business_name": "Deshmukh Electricals", "owner_name": "Vijay Deshmukh",
                "email_prefix": "deshmukh.electricals", "gstin": "27DDDPR4444F1Z1",
                "mobile": "9800000003", "address": "MG Road, Kolhapur",
                "assigned_to": "partner",
                "bills": [
                    bill(5, "Ruchi Electricals", "27AABCS4444N1Z1", 56000, 18, False, "pending_review", 2),
                    bill(6, "Shree Cables", "07AAGCT5555P1Z6", 31500, 18, False, "approved", 12),
                ],
            },
            {
                "business_name": "Joshi Mobiles", "owner_name": "Deepak Joshi",
                "email_prefix": "joshi.mobiles", "gstin": "27HHHPJ8888K1Z9",
                "mobile": "9800000007", "address": "Camp Road, Pune",
                "assigned_to": "junior", "status": "pending", "bills": [],
            },
        ],
    },
    {
        "key": "mehta",
        "name": "Mehta Shah and Co",
        "gstin": "27AABFM5678B1Z2",
        "address": "45 Dalal Street, Mumbai, Maharashtra 400001",
        "invoice_prefix": "MSC",
        "ca": {"name": "Rahul Mehta", "email_prefix": "partner.mehta", "membership_number": "345678"},
        "junior": {"name": "Priya Shah", "email_prefix": "junior.mehta", "membership_number": "456789"},
        "clients": [
            {
                "business_name": "Gupta Hardware", "owner_name": "Manoj Gupta",
                "email_prefix": "gupta.hardware", "gstin": "27EEEPK5555G1Z3",
                "mobile": "9800000004", "address": "Lohar Chawl, Mumbai",
                "assigned_to": "junior",
                "bills": [
                    bill(1, "Bharat Tools Depot", "27AAACB8888R1Z2", 18000, 18, False, "uploaded", 1),
                    bill(2, "Metro Fasteners", "24AAECM9999S1Z0", 27500, 18, True, "approved", 8),
                ],
            },
            {
                "business_name": "Iyer Medical Store", "owner_name": "Lakshmi Iyer",
                "email_prefix": "iyer.medical", "gstin": "27FFFPL6666H1Z5",
                "mobile": "9800000005", "address": "Matunga East, Mumbai",
                "assigned_to": "junior",
                "bills": [
                    bill(3, "Healthline Distributors", "27AABCH1010T1Z4", 64000, 12, False, "pending_review", 2),
                    bill(4, "Quick Pharma", "29AABCQ2020U1Z6", 9500, 5, True, "rejected", 5),
                ],
            },
            {
                "business_name": "Khan Garments", "owner_name": "Imran Khan",
                "email_prefix": "khan.garments", "gstin": "27GGGPK7777J1Z7",
                "mobile": "9800000006", "address": "Crawford Market, Mumbai",
                "assigned_to": "partner",
                "bills": [
                    bill(5, "Fabric World", "27AAACF3030V1Z8", 48000, 5, False, "pending_review", 3),
                    bill(6, "Silk Route Textiles", "33AAHCS4040W1Z1", 72000, 12, True, "approved", 10),
                ],
            },
            {
                "business_name": "Naik Agro Traders", "owner_name": "Sanjay Naik",
                "email_prefix": "naik.agro", "gstin": "27IIIPN9999L1Z1",
                "mobile": "9800000008", "address": "APMC Market, Vashi",
                "assigned_to": "junior", "status": "pending", "bills": [],
            },
        ],
    },
]