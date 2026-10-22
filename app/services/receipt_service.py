import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_booking_receipt_pdf(booking):
    """
    Generates a professional, branded PDF booking receipt and tax invoice
    for short stay accommodations using ReportLab.
    Returns a BytesIO buffer containing the PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography & styles
    primary_color = colors.HexColor('#0284c7')
    secondary_dark = colors.HexColor('#0f172a')
    muted_color = colors.HexColor('#64748b')
    border_color = colors.HexColor('#cbd5e1')
    table_header_bg = colors.HexColor('#f1f5f9')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=muted_color
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=secondary_dark,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=secondary_dark
    )

    body_muted = ParagraphStyle(
        'BodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=muted_color
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=secondary_dark
    )

    right_bold = ParagraphStyle(
        'RightBold',
        parent=body_bold,
        alignment=TA_RIGHT
    )

    right_body = ParagraphStyle(
        'RightBody',
        parent=body_style,
        alignment=TA_RIGHT
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>PG FINDER BENGALURU</b>", title_style),
            Paragraph(f"<b>BOOKING CONFIRMATION & TAX INVOICE</b><br/><font color='#0284c7'><b>REF: {booking.booking_code}</b></font>", right_bold)
        ],
        [
            Paragraph("Verified Student & Working Professional Accommodations<br/>Karnataka, India • support@pgfinder.in", subtitle_style),
            Paragraph(f"Date Issued: {booking.created_at.strftime('%d %b %Y, %I:%M %p')}<br/>Status: <b>{booking.status.upper()}</b> | Payment: <b>{booking.payment_status.upper()}</b>", right_body)
        ]
    ]

    header_table = Table(header_data, colWidths=[290, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # 2. Stay & Property Overview Card
    prop = booking.property
    owner = prop.owner if prop else None
    customer = booking.customer
    cfg = prop.short_stay_config if prop else None

    cin_time = cfg.check_in_time if cfg else "12:00 PM"
    cout_time = cfg.check_out_time if cfg else "11:00 AM"

    stay_info_data = [
        [
            Paragraph("<b>PROPERTY & OWNER DETAILS</b>", h2_style),
            Paragraph("<b>GUEST & RESERVATION DETAILS</b>", h2_style)
        ],
        [
            Paragraph(f"<b>{prop.name if prop else 'N/A'}</b><br/>"
                      f"{prop.address if prop else ''}, {prop.locality if prop else ''}<br/>"
                      f"Bengaluru, Karnataka - {prop.pincode if prop else '560001'}<br/>"
                      f"<b>Host / Owner:</b> {owner.name if owner else 'Host'} ({owner.phone if owner else 'N/A'})", body_style),
            Paragraph(f"<b>Lead Guest:</b> {customer.name if customer else 'Guest'}<br/>"
                      f"<b>Phone:</b> {customer.phone if customer else 'N/A'} • <b>Email:</b> {customer.email if customer else 'N/A'}<br/>"
                      f"<b>Total Guests:</b> {booking.num_guests} person(s)<br/>"
                      f"<b>Room Category:</b> {booking.room_type.title if booking.room_type else 'Standard Short Stay Room'}", body_style)
        ]
    ]

    stay_table = Table(stay_info_data, colWidths=[260, 260])
    stay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(stay_table)
    story.append(Spacer(1, 12))

    # 3. Schedule Dates Bar
    schedule_data = [
        [
            Paragraph("<b>CHECK-IN DATE</b>", body_muted),
            Paragraph("<b>CHECK-OUT DATE</b>", body_muted),
            Paragraph("<b>TOTAL DURATION</b>", body_muted)
        ],
        [
            Paragraph(f"<b>{booking.check_in_date.strftime('%a, %d %b %Y')}</b><br/>From {cin_time}", body_style),
            Paragraph(f"<b>{booking.check_out_date.strftime('%a, %d %b %Y')}</b><br/>By {cout_time}", body_style),
            Paragraph(f"<b>{booking.nights} Night(s)</b>", body_style)
        ]
    ]
    sched_table = Table(schedule_data, colWidths=[173, 173, 174])
    sched_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2fe')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bae6fd')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bae6fd')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(sched_table)
    story.append(Spacer(1, 14))

    # 4. Itemized Cost Breakdown Table
    story.append(Paragraph("<b>ITEMIZED CHARGES & TAX BREAKDOWN</b>", h2_style))

    pricing_desc = f"Room Stay ({booking.nights} nights @ standard/tiered rate)"
    extra_guests_count = max(0, booking.num_guests - (cfg.base_guests if cfg else 1))

    bill_items = [
        [Paragraph("<b>Item Description</b>", body_bold), Paragraph("<b>Rate / Calculation</b>", body_bold), Paragraph("<b>Amount (INR)</b>", right_bold)],
        [
            Paragraph(pricing_desc, body_style),
            Paragraph(f"₹{booking.daily_rate_applied:,.2f} / night", body_style),
            Paragraph(f"₹{booking.base_amount:,.2f}", right_body)
        ]
    ]

    if extra_guests_count > 0:
        extra_charge_per_night = cfg.extra_guest_charge if cfg else 350.0
        bill_items.append([
            Paragraph(f"Extra Guest Charges ({extra_guests_count} guest(s))", body_style),
            Paragraph(f"{extra_guests_count} x ₹{extra_charge_per_night:,.0f} x {booking.nights} nights", body_style),
            Paragraph(f"₹{booking.extra_guests_amount:,.2f}", right_body)
        ])

    if booking.cleaning_fee > 0:
        bill_items.append([
            Paragraph("Cleaning & Linen Preparation Fee", body_style),
            Paragraph("One-time sanitation fee", body_style),
            Paragraph(f"₹{booking.cleaning_fee:,.2f}", right_body)
        ])

    subtotal = booking.base_amount + booking.extra_guests_amount + booking.cleaning_fee
    bill_items.append([
        Paragraph("<b>Taxable Subtotal</b>", body_bold),
        Paragraph("", body_style),
        Paragraph(f"<b>₹{subtotal:,.2f}</b>", right_bold)
    ])

    if booking.tax_amount > 0:
        tax_pct = cfg.tax_percentage if cfg else 5.0
        bill_items.append([
            Paragraph(f"Goods & Services Tax (GST {tax_pct}%)", body_style),
            Paragraph("Applicable government tax", body_style),
            Paragraph(f"₹{booking.tax_amount:,.2f}", right_body)
        ])

    if booking.security_deposit > 0:
        bill_items.append([
            Paragraph("Refundable Security Deposit", body_style),
            Paragraph("100% refundable at check-out inspection", body_style),
            Paragraph(f"₹{booking.security_deposit:,.2f}", right_body)
        ])

    bill_items.append([
        Paragraph("<b>TOTAL RESERVATION AMOUNT</b>", title_style),
        Paragraph("", body_style),
        Paragraph(f"<b>₹{booking.total_amount:,.2f}</b>", title_style)
    ])

    total_paid = booking.total_paid
    balance_due = booking.balance_due

    bill_items.append([
        Paragraph("<b>Total Amount Paid to Date</b>", body_bold),
        Paragraph(f"Status: {booking.payment_status.replace('_', ' ').capitalize()}", body_style),
        Paragraph(f"<font color='#16a34a'><b>₹{total_paid:,.2f}</b></font>", right_bold)
    ])

    bill_items.append([
        Paragraph("<b>Remaining Balance Due</b>", body_bold),
        Paragraph("Payable upon arrival / check-in", body_style),
        Paragraph(f"<font color='#dc2626'><b>₹{balance_due:,.2f}</b></font>", right_bold)
    ])

    bill_table = Table(bill_items, colWidths=[240, 160, 120])
    bill_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, -3), (-1, -3), 1.5, primary_color),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 14))

    # 5. Payment Transaction Records (if any)
    if booking.payments:
        story.append(Paragraph("<b>PAYMENT TRANSACTION HISTORY</b>", h2_style))
        pay_rows = [
            [Paragraph("<b>Receipt #</b>", body_bold), Paragraph("<b>Transaction Ref</b>", body_bold),
             Paragraph("<b>Method</b>", body_bold), Paragraph("<b>Date & Time</b>", body_bold),
             Paragraph("<b>Amount</b>", right_bold)]
        ]
        for p in booking.payments:
            pay_rows.append([
                Paragraph(p.receipt_number, body_style),
                Paragraph(p.transaction_id[:20] if p.transaction_id else 'N/A', body_style),
                Paragraph(p.payment_method or 'UPI', body_style),
                Paragraph(p.paid_at.strftime('%d %b %Y, %I:%M %p'), body_style),
                Paragraph(f"₹{p.amount:,.2f}", right_bold)
            ])
        pay_table = Table(pay_rows, colWidths=[100, 140, 80, 120, 80])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
            ('BOX', (0, 0), (-1, -1), 1, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 12))

    # 6. Terms, House Rules & Footer
    rules_text = cfg.short_stay_rules if (cfg and cfg.short_stay_rules) else "Govt photo ID required at check-in. Maintain peace and follow PG guidelines."
    cancellation_text = cfg.cancellation_policy if (cfg and cfg.cancellation_policy) else "Free cancellation up to 24 hours prior to check-in date."

    footer_content = [
        Paragraph("<b>CANCELLATION & HOUSE RULES</b>", h2_style),
        Paragraph(f"• <b>Cancellation Terms:</b> {cancellation_text}", body_style),
        Paragraph(f"• <b>House Rules:</b> {rules_text}", body_style),
        Spacer(1, 10),
        Paragraph("<i>This is a computer-generated tax invoice and booking confirmation from PG Finder Bengaluru. No physical signature required. Have a wonderful stay in Bengaluru!</i>", body_muted)
    ]
    story.append(KeepTogether(footer_content))

    doc.build(story)
    buffer.seek(0)
    return buffer
