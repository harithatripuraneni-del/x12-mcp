"""A small, hand-written reference of common X12 segments and codes.

This is intentionally not exhaustive. It covers the envelopes plus the
logistics documents this project focuses on (204, 210, 214, 990, 997).
"""

SEGMENTS: dict[str, str] = {
    # Envelopes
    "ISA": "Interchange Control Header: sender, receiver, date and control number for the whole file",
    "IEA": "Interchange Control Trailer: number of groups and the ISA control number",
    "GS": "Functional Group Header: starts a batch of one document type",
    "GE": "Functional Group Trailer: number of transactions and the GS control number",
    "ST": "Transaction Set Header: starts one business document",
    "SE": "Transaction Set Trailer: segment count and the ST control number",
    # Logistics
    "B2": "Beginning Segment for Shipment Information (204 load tender)",
    "B2A": "Set Purpose: new, change or cancel (204)",
    "B3": "Beginning Segment for Carrier's Invoice (210)",
    "B1": "Beginning Segment for Booking or Pick-up/Delivery (990 response)",
    "B10": "Beginning Segment for Transportation Carrier Shipment Status (214)",
    "S5": "Stop Off Details: one pickup or delivery stop",
    "L11": "Business Instructions and Reference Number",
    "G62": "Date/Time",
    "N1": "Party Identification: shipper, consignee, bill-to and so on",
    "N3": "Party Location: street address",
    "N4": "Geographic Location: city, state, postal code",
    "LX": "Transaction Set Line Number: groups the segments that follow",
    "AT7": "Shipment Status Details: status code, date and time",
    "AT8": "Shipment Weight, Packaging and Quantity Data",
    "MS1": "Equipment, Shipment or Real Property Location: city and state of a status",
    "MS2": "Equipment or Container Owner and Type",
    "L3": "Total Weight and Charges",
    "L5": "Description, Marks and Numbers",
    "NTE": "Note/Special Instruction",
    # Acknowledgments
    "AK1": "Functional Group Response Header (997)",
    "AK2": "Transaction Set Response Header (997)",
    "AK5": "Transaction Set Response Trailer: accepted or rejected (997)",
    "AK9": "Functional Group Response Trailer (997)",
}

TRANSACTION_SETS: dict[str, str] = {
    "204": "Motor Carrier Load Tender",
    "210": "Motor Carrier Freight Details and Invoice",
    "214": "Transportation Carrier Shipment Status Message",
    "990": "Response to a Load Tender",
    "997": "Functional Acknowledgment",
    "850": "Purchase Order",
    "810": "Invoice",
    "856": "Ship Notice/Manifest",
}

# GS01 functional identifier expected for each transaction set.
FUNCTIONAL_IDS: dict[str, str] = {
    "204": "SM",
    "210": "IM",
    "214": "QM",
    "990": "GF",
    "997": "FA",
    "850": "PO",
    "810": "IN",
    "856": "SH",
}

# Segments a transaction set cannot do without. Kept deliberately minimal.
REQUIRED_SEGMENTS: dict[str, list[str]] = {
    "204": ["B2", "B2A", "S5"],
    "210": ["B3"],
    "214": ["B10"],
    "990": ["B1"],
    "997": ["AK1", "AK9"],
}

# Common AT701 shipment status codes (not the full code list).
SHIPMENT_STATUS: dict[str, str] = {
    "X3": "Arrived at pickup location",
    "AF": "Departed pickup location with shipment",
    "X6": "En route to delivery location",
    "AG": "Estimated delivery",
    "X1": "Arrived at delivery location",
    "D1": "Completed unloading at delivery location",
    "CD": "Carrier departed delivery location",
    "SD": "Shipment delayed",
}

PARTY_ROLES: dict[str, str] = {
    "SH": "Shipper",
    "CN": "Consignee",
    "BT": "Bill-to party",
    "SF": "Ship from",
    "ST": "Ship to",
}
