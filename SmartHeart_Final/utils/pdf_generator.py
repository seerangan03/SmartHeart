"""
SmartHeart - Professional PDF Report Generator
Clean, single-page A4. Matches reference screenshot exactly.
"""
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
    C_NAVY  = colors.HexColor('#0a1929')
    C_BLUE  = colors.HexColor('#1a6fc4')
    C_BLUEL = colors.HexColor('#e8f4fd')
    C_SLATE = colors.HexColor('#4e6080')
    C_MUTED = colors.HexColor('#7c94b2')
    C_BDR   = colors.HexColor('#dce6f0')
    C_SURF  = colors.HexColor('#f5f8fc')
    C_WHITE = colors.white
    C_GREEN = colors.HexColor('#059669')
    SEV_C   = {
        'Low':      colors.HexColor('#059669'),
        'Moderate': colors.HexColor('#ca8a04'),
        'High':     colors.HexColor('#ea580c'),
        'Critical': colors.HexColor('#dc2626'),
    }
except ImportError:
    REPORTLAB_AVAILABLE = False

CHEST_LBL = {
    '0': 'Typical Angina', '1': 'Atypical Angina',
    '2': 'Non-Anginal Pain', '3': 'Asymptomatic',
}
CSUMM = {
    'Low':      'All cardiovascular indicators within healthy ranges. Routine monitoring and healthy lifestyle maintenance are sufficient.',
    'Moderate': 'Several risk factors identified above baseline. Medical consultation and lifestyle modification are recommended.',
    'High':     'Multiple significant cardiac risk factors present. Prompt cardiology referral and further investigations are required.',
    'Critical': 'Critical cardiac risk profile. Immediate emergency cardiology evaluation is required without delay.',
}
INTERP = {
    'Low':      ('The patient presents with cardiovascular indicators within clinically acceptable ranges. '
                 'No immediate cardiac intervention is indicated. The recommended management plan includes: '
                 '[1] Continuation of current healthy lifestyle practices; [2] Regular aerobic exercise, minimum 150 min/week; '
                 '[3] Annual lipid panel, blood pressure, and glucose screening; '
                 '[4] Adherence to a heart-healthy dietary pattern, Mediterranean or DASH diet; '
                 '[5] Avoidance of tobacco products and excess alcohol consumption.'),
    'Moderate': ('The patient presents with several cardiovascular risk factors requiring medical attention. '
                 'A physician consultation within 2-4 weeks is recommended. The management plan includes: '
                 '[1] Physician consultation for cardiovascular risk assessment; [2] Home blood pressure monitoring; '
                 '[3] Dietary sodium restriction to below 2,300 mg/day; [4] Supervised exercise programme; '
                 '[5] Fasting lipid panel reassessment and pharmacological options discussion.'),
    'High':     ('The patient presents with multiple significant cardiac risk factors requiring prompt intervention. '
                 'A cardiology referral within 1 week is strongly recommended. The management plan includes: '
                 '[1] Urgent cardiology consultation and risk stratification; [2] 12-lead ECG and exercise stress test; '
                 '[3] Echocardiogram evaluation; [4] Review and optimisation of current medications; '
                 '[5] Avoidance of strenuous unsupervised physical activity until medically cleared.'),
    'Critical': ('The patient presents with a critical cardiac risk profile requiring immediate emergency evaluation. '
                 'Emergency cardiology assessment without delay is mandatory. The recommended immediate actions include: '
                 '[1] Immediate emergency cardiology visit - do not delay; '
                 '[2] Call 112/911 if experiencing chest pain, shortness of breath, or palpitations; '
                 '[3] Do not operate a vehicle - arrange emergency transport immediately; '
                 '[4] Coronary angiography and advanced cardiac imaging may be required; '
                 '[5] ICU or cardiac care unit admission is likely indicated.'),
}


def _s(name, **kw):
    base = dict(fontName='Helvetica', fontSize=9, textColor=colors.black, leading=12)
    base.update(kw)
    return ParagraphStyle(name, **base)


def _p(txt, **kw):
    return Paragraph(txt, _s(f'p{abs(hash(txt+str(kw)))%9999}', **kw))


def _tick(ok, warn=False):
    """Coloured status text. ZapfDingbats '4'=✓, '8'=✗."""
    if ok:
        return _p('<font name="ZapfDingbats" color="#059669" size="9">4</font>'
                  '<font color="#059669"> Normal</font>', fontSize=8.5, alignment=TA_CENTER)
    elif warn:
        return _p('<font color="#92400e">~ Borderline</font>', fontSize=8.5, alignment=TA_CENTER)
    return _p('<font name="ZapfDingbats" color="#991b1b" size="9">8</font>'
              '<font color="#991b1b"> Abnormal</font>', fontSize=8.5, alignment=TA_CENTER)


def _dash():
    return _p('\u2014', fontSize=8.5, textColor=C_MUTED, alignment=TA_CENTER)


def generate_pdf_report(report, patient_name, output_path):
    if not REPORTLAB_AVAILABLE:
        return False, 'ReportLab not installed. Run: pip install reportlab'

    sev        = str(report.get('severity', 'Low'))
    score      = float(report.get('risk_score', 0))
    ref_id     = str(report.get('ref_id', 'N/A'))
    created_at = str(report.get('created_at', ''))[:16]
    gender_str = 'Male' if str(report.get('gender', '')) == '1' else 'Female'
    chest_str  = CHEST_LBL.get(str(report.get('chest_pain', '')), 'Unknown')
    method_str = str(report.get('input_method', 'Manual')).title()
    remarks    = str(report.get('doctor_remarks', '') or '').strip()

    sc    = SEV_C.get(sev, C_MUTED)
    csumm = CSUMM.get(sev, '')
    ibody = INTERP.get(sev, '')

    bp   = int(report.get('bp', 0))
    chol = int(report.get('cholesterol', 0))
    hr   = int(report.get('heart_rate', 0))
    sug  = str(report.get('sugar', '0'))
    age_v = str(report.get('age', '\u2014'))

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=14*mm, leftMargin=14*mm,
        topMargin=8*mm, bottomMargin=8*mm,
        title=f'SmartHeart Report {ref_id}',
        author='SmartHeart Cardiac AI System'
    )
    PW = A4[0] - 28*mm
    elems = []

    # ══ 1. HEADER BAND ══════════════════════════════════════
    hdr = Table([[
        _p('<font color="white" size="14"><b>\u2764 SmartHeart</b></font><br/>'
           '<font color="#93c5e4" size="8">Cardiac Intelligence Platform</font>',
           fontName='Helvetica-Bold', fontSize=14, textColor=C_WHITE, leading=18),
        _p('<font color="#93c5e4" size="7.5">CARDIAC RISK ASSESSMENT</font><br/>'
           '<font color="#93c5e4" size="7.5">REPORT \u2014 CONFIDENTIAL</font><br/>'
           f'<font color="white" size="8.5"><b>{ref_id}</b></font>',
           fontSize=8.5, textColor=C_WHITE, alignment=TA_RIGHT, leading=12),
    ]], colWidths=[PW * .60, PW * .40])
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_NAVY),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
        ('RIGHTPADDING', (0,0), (-1,-1), 16),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elems += [hdr, Spacer(1, 2*mm)]

    # ══ 2. META ROW ═════════════════════════════════════════
    meta = Table([[
        _p(f'<font color="#7c94b2" size="7.5">PATIENT</font><br/>'
           f'<font size="9.5"><b>{patient_name}</b></font>',
           fontName='Helvetica-Bold', fontSize=9.5, leading=13),
        _p(f'<font color="#7c94b2" size="7.5">DATE GENERATED</font><br/>'
           f'<font size="9">{created_at}</font>',
           fontSize=9, leading=13),
        _p(f'<font color="#7c94b2" size="7.5">INPUT METHOD</font><br/>'
           f'<font size="9">{method_str}</font>',
           fontSize=9, leading=13),
        _p('<font color="#7c94b2" size="7.5">REPORT STATUS</font><br/>'
           '<font color="#059669" size="9"><b>Finalized</b></font>',
           fontSize=9, fontName='Helvetica-Bold', leading=13),
    ]], colWidths=[PW*.30, PW*.25, PW*.22, PW*.23])
    meta.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, C_BDR),
        ('LINEBEFORE', (1,0), (-1,-1), 0.5, C_BDR),
        ('BACKGROUND', (0,0), (-1,-1), C_SURF),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
    ]))
    elems += [meta, Spacer(1, 2.5*mm)]

    # ══ 3. RISK HERO — single row, 3 cells, each with label+value stacked ══
    # Using single-row prevents height mismatch bugs seen in 2-row approach
    sev_desc = {
        'Low': 'Cardiac health is stable',
        'Moderate': 'Medical attention advised',
        'High': 'Urgent cardiology needed',
        'Critical': 'Immediate emergency required'
    }[sev]

    cell_a = _p(
        '<font color="#93c5e4" size="8"><b>CARDIAC RISK SCORE</b></font><br/><br/>'
        f'<font color="white" size="32"><b>{score}%</b></font>',
        fontSize=32, fontName='Helvetica-Bold', textColor=C_WHITE,
        alignment=TA_CENTER, leading=40
    )
    cell_b = _p(
        '<font color="#93c5e4" size="8"><b>SEVERITY LEVEL</b></font><br/><br/>'
        f'<font color="white" size="18"><b>{sev.upper()}</b></font><br/>'
        f'<font color="white" size="7">{sev_desc}</font>',
        fontSize=18, fontName='Helvetica-Bold', textColor=C_WHITE,
        alignment=TA_CENTER, leading=24
    )
    cell_c = _p(
        '<font color="#93c5e4" size="8"><b>CLINICAL SUMMARY</b></font><br/><br/>'
        f'<font color="white" size="8.5">{csumm}</font>',
        fontSize=8.5, textColor=C_WHITE, leading=13
    )
    hero = Table([[cell_a, cell_b, cell_c]], colWidths=[PW*.27, PW*.23, PW*.50])
    hero.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), C_BLUE),
        ('BACKGROUND', (1,0), (1,-1), sc),
        ('BACKGROUND', (2,0), (2,-1), C_NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  (0,0), (1,-1), 'CENTER'),
        ('ALIGN',  (2,0), (2,-1), 'LEFT'),
    ]))
    elems += [hero, Spacer(1, 3.5*mm)]

    # ══ 4. CLINICAL VITALS TABLE ════════════════════════════
    elems.append(_p('<b>Clinical Vitals &amp; Parameters</b>',
                    fontSize=10, fontName='Helvetica-Bold', textColor=C_NAVY, spaceAfter=4))

    def vrow(param, val, ref, stat):
        return [
            _p(param, fontSize=8.5),
            _p(f'<b>{val}</b>', fontName='Helvetica-Bold', fontSize=8.5, alignment=TA_CENTER),
            _p(ref, fontSize=8.5, textColor=C_SLATE, alignment=TA_CENTER),
            stat,
        ]

    sug_val = 'Normal' if sug != '1' else 'Elevated'
    vdata = [
        [_p('<b>Parameter</b>',      fontName='Helvetica-Bold', fontSize=8.5, textColor=C_WHITE),
         _p('<b>Result</b>',          fontName='Helvetica-Bold', fontSize=8.5, textColor=C_WHITE, alignment=TA_CENTER),
         _p('<b>Reference Range</b>', fontName='Helvetica-Bold', fontSize=8.5, textColor=C_WHITE, alignment=TA_CENTER),
         _p('<b>Status</b>',          fontName='Helvetica-Bold', fontSize=8.5, textColor=C_WHITE, alignment=TA_CENTER)],
        vrow('Age',                   f'{age_v} years',   '\u2014',        _dash()),
        vrow('Gender',                gender_str,          '\u2014',        _dash()),
        vrow('Blood Pressure (Systolic)', f'{bp} mmHg',  '90-120 mmHg',  _tick(90<=bp<=120, 120<bp<=140)),
        vrow('Serum Cholesterol',     f'{chol} mg/dL',    '&lt;200 mg/dL', _tick(chol<200, 200<=chol<240)),
        vrow('Heart Rate',            f'{hr} bpm',         '60-100 bpm',   _tick(60<=hr<=100)),
        vrow('Fasting Blood Sugar',   f'{sug_val} (&lt;120 mg/dL)' if sug != '1' else 'Elevated',
                                      '&lt;120 mg/dL',   _tick(sug != '1')),
        vrow('Chest Pain Type',       chest_str,           '\u2014',        _dash()),
    ]
    vtbl = Table(vdata, colWidths=[PW*.42, PW*.20, PW*.22, PW*.16])
    vtbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_SURF]),
        ('GRID',          (0,0), (-1,-1), 0.4, C_BDR),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('FONTSIZE',      (0,0), (-1,-1), 8.5),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elems += [vtbl, Spacer(1, 3.5*mm)]

    # ══ 5. INTERPRETATION & RECOMMENDATIONS (full-width) ════
    elems.append(_p('<b>Clinical Interpretation &amp; Recommendations</b>',
                    fontSize=10, fontName='Helvetica-Bold', textColor=C_NAVY, spaceAfter=4))
    ibox = Table([[
        _p(f'<font size="8" color="#374151">{ibody}</font>',
           fontSize=8, textColor=colors.HexColor('#374151'), leading=13, alignment=TA_JUSTIFY)
    ]], colWidths=[PW])
    ibox.setStyle(TableStyle([
        ('BOX',          (0,0), (-1,-1), 1, sc),
        ('BACKGROUND',   (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('TOPPADDING',   (0,0), (-1,-1), 12),
        ('BOTTOMPADDING',(0,0), (-1,-1), 12),
        ('LEFTPADDING',  (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
    ]))
    elems.append(ibox)

    # ══ 6. DOCTOR REMARKS ═══════════════════════════════════
    if remarks:
        elems.append(Spacer(1, 3*mm))
        rmbox = Table([[
            _p('<font color="#1a6fc4" size="8.5"><b>PHYSICIAN\'S REMARKS</b></font><br/>'
               f'<font size="8.5">{remarks}</font>', fontSize=8.5, leading=13)
        ]], colWidths=[PW])
        rmbox.setStyle(TableStyle([
            ('BOX',          (0,0), (-1,-1), 0.5, C_BDR),
            ('BACKGROUND',   (0,0), (-1,-1), C_BLUEL),
            ('TOPPADDING',   (0,0), (-1,-1), 10),
            ('BOTTOMPADDING',(0,0), (-1,-1), 10),
            ('LEFTPADDING',  (0,0), (-1,-1), 13),
            ('RIGHTPADDING', (0,0), (-1,-1), 13),
        ]))
        elems.append(rmbox)

    # ══ 7. FOOTER ═══════════════════════════════════════════
    elems += [
        Spacer(1, 3*mm),
        HRFlowable(width='100%', thickness=0.5, color=C_BDR),
        Spacer(1, 2*mm),
        _p(f'<font color="#7c94b2" size="7">'
           f'Generated by SmartHeart Cardiac AI System \u00b7 {created_at} \u00b7 Ref: {ref_id} \u00b7 '
           f'This report is AI-assisted and must be reviewed by a qualified clinician before any medical decision.'
           f'</font>',
           fontSize=7, textColor=C_MUTED, alignment=TA_CENTER, leading=10),
    ]

    try:
        doc.build(elems)
        return True, output_path
    except Exception as e:
        return False, str(e)
