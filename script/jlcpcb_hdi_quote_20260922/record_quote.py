"""Record visible JLCPCB quote evidence and fresh native verification."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'QSTL_24DC_4MW_PCB'
OUT = PROJECT / 'fabrication' / 'JLCPCB_HDI_20260922'
report = json.loads((OUT / 'CAM_validation.json').read_text())
assert 'AFTER_REOPEN_COUNT=0' in (OUT / 'reopen_check.txt').read_text()
assert 'AFTER_DRC_COUNT=0' in (OUT / 'reopen_check.txt').read_text()
assert 'COMPLETE' in (OUT / 'reopen_check.txt').read_text()
assert hashlib.sha256((PROJECT / 'QSTL_24DC_4MW_PCB.PcbDoc').read_bytes()).hexdigest() == report['pcb_sha256']
report['fresh_native_reopen_20260922'] = {
    'stored_connections_after_reopen': 0,
    'stored_connections_after_DRC': 0,
    'DRC_report': 'Native_DRC.html',
    'violations': 0,
    'checked_rules': 15,
    'pcb_unchanged_after_export_and_reopen': True,
}
(OUT / 'CAM_validation.json').write_text(json.dumps(report, indent=2) + '\n')
quote = {
    'observed_date': '2026-09-22',
    'url': 'https://cart.jlcpcb.com/quote',
    'currency': 'USD',
    'quantity': 5,
    'pcb_price': 291.99,
    'shipping_country_assumption': 'Canada',
    'shipping_method': 'DHL Express',
    'shipping_price': 28.08,
    'subtotal_before_tax_and_manual_adjustments': 320.07,
    'PCB_build_time_display': '12-13 days',
    'shipping_time_display': '2-4 business days',
    'manual_quote_lines': ['Buried Via Fee', 'Lamination Fee'],
    'blind_slot': {'side': 'Bottom', 'plated': False, 'depth_mm': 1.2, 'size_mm': [4.3, 4.3], 'radius_mm': 0.5},
    'blind_laser_holes': {'count': 480, 'span': ['L5', 'L6'], 'hole_mm': 0.1, 'land_mm': 0.25},
    'selected_options': json.loads((OUT / 'JLC_selected_options.json').read_text()),
    'PCBA': False,
    'stencil': False,
    'firm_manufacturer_quote': False,
    'quote_captured_before_login': True,
    'account_access': {
        'requested_account': 'QSTL DOTS',
        'login_succeeded': True,
        'restriction_notice_shown': True,
        'announced_closure_date': '2026-11-21',
        'quote_redirected_to_restriction_notice': True,
        'manufacturer_viewer_span_confirmation': 'Blocked by account restriction',
        'quote_saved_to_requested_account': False,
        'notice_url': 'https://jlcpcb.com/help/article/notice-of-limited-account-access-restrictions',
        'evidence': '09_Account_restriction_notice.png',
    },
    'order_placed': False,
}
(OUT / 'Quote_summary.json').write_text(json.dumps(quote, indent=2) + '\n')
print('Fresh native checks recorded; original PCB unchanged.')
