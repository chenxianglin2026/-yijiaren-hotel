#!/usr/bin/env python3
"""Batch fix WXSS font sizes for accessibility (适老化 ×1.4).
- Body/title/button text with font-size < 28rpx → 28rpx
- Label/tip/auxiliary text with font-size < 24rpx → 24rpx
- Already at 24rpx (labels/tips) → keep as-is
"""
import re
import os

MINIAPP_DIR = os.path.dirname(os.path.abspath(__file__))

# Per-file rules: (selector_contains, old_size, new_size)
# body/title/button changes: < 28rpx → 28rpx
BODY_UPGRADES = [
    # login.wxss
    ("login-subtitle", 26, 28),
    ("code-btn", 26, 28),
    # booking.wxss
    ("form-input", 26, 28),
    ("form-picker", 26, 28),
    ("form-textarea", 26, 28),
    # index.wxss
    ("search-input", 26, 28),
    ("search-clear", 26, 28),
    ("filter-btn", 26, 28),
    ("loading-text", 26, 28),
    ("btn-sm", 26, 28),
    # mine.wxss
    ("user-phone", 26, 28),
    # service.wxss
    ("form-textarea", 26, 28),
    ("priority-item", 26, 28),
    # room.wxss
    ("room-desc", 26, 28),
    ("highlight-text", 26, 28),
    ("detail-value", 26, 28),
    ("review-user", 26, 28),
    ("btn-outline", 26, 28),
    # hotel.wxss
    ("addr-text", 26, 28),
    ("contact-text", 26, 28),
    ("store-desc", 26, 28),
    ("highlight-text", 26, 28),
    ("btn-sm", 26, 28),
    # cleaning.wxss
    ("btn-accept", 26, 28),
    ("btn-start", 26, 28),
    ("btn-checkin", 26, 28),
    ("btn-detail", 26, 28),
    ("checkin-note", 26, 28),
    ("photo-retake", 22, 28),
    # checkin.wxss
    ("info-value", 26, 28),
    ("ble-step-text", 26, 28),
    ("nearby-name", 26, 28),
    # app.wxss
    ("btn-ghost", 26, 28),
    # orders.wxss
    ("btn-sm", 24, 28),
]

# Label/tip/auxiliary changes: < 24rpx → 24rpx
LABEL_UPGRADES = [
    # login.wxss
    ("footer-text", 22, 24),
    # orders.wxss
    ("tab-badge", 20, 24),
    ("summary-label", 22, 24),
    ("order-date", 22, 24),
    # booking.wxss
    ("date-label", 22, 24),
    ("date-week", 22, 24),
    ("nights-text", 22, 24),
    # index.wxss
    ("location-arrow", 22, 24),
    ("feature-desc", 20, 24),
    ("room-tag-item", 20, 24),
    ("room-type-tag", 22, 24),
    ("meta-item", 22, 24),
    ("price-original", 22, 24),
    ("room-stock", 22, 24),
    # mine.wxss
    ("member-points", 22, 24),
    ("stat-label", 22, 24),
    ("action-label", 22, 24),
    ("menu-desc", 22, 24),
    ("menu-badge", 20, 24),
    # service.wxss
    ("service-desc", 22, 24),
    ("quick-label", 22, 24),
    ("request-status", 22, 24),
    ("request-room", 22, 24),
    ("request-time", 22, 24),
    ("form-count", 22, 24),
    # room.wxss
    ("swiper-counter-text", 22, 24),
    ("legend-text", 20, 24),
    ("cal-week-day", 22, 24),
    ("cal-day-price", 18, 24),
    ("detail-label", 22, 24),
    ("review-tag", 22, 24),
    ("review-date", 22, 24),
    # hotel.wxss
    ("store-meta-tag", 22, 24),
    ("facility-label", 22, 24),
    ("nearby-distance", 22, 24),
    ("room-tag-item", 20, 24),
    ("room-type-tag", 22, 24),
    ("meta-item", 22, 24),
    ("price-original", 22, 24),
    ("room-stock", 22, 24),
    ("bottom-icon-label", 18, 24),
    # cleaning.wxss
    ("stat-label", 22, 24),
    ("task-type-tag", 22, 24),
    ("task-time", 22, 24),
    ("photo-sub", 22, 24),
    ("note-count", 22, 24),
    # checkin.wxss
    ("info-label", 22, 24),
    ("idcard-sub", 20, 24),
    ("ble-step-num", 22, 24),
    ("service-desc", 20, 24),
    # app.wxss
    ("tag", 22, 24),
]

# Some labels that are already at 26rpx but should be kept at 24rpx (downgrade)
LABEL_DOWNGRADES = [
    # booking.wxss
    ("form-label", 26, 24),
    # index.wxss
    ("filter-label", 26, 24),
    # service.wxss
    ("form-label", 26, 24),
]

def find_wxss_files():
    files = []
    for root, dirs, filenames in os.walk(MINIAPP_DIR):
        for f in filenames:
            if f.endswith('.wxss'):
                files.append(os.path.join(root, f))
    return sorted(files)

def apply_upgrade(content, rules, target_size_label):
    """Apply font-size upgrades. rules: list of (selector_hint, old_size, new_size)."""
    changes = 0
    for selector_hint, old_val, new_val in rules:
        # Match: the selector_hint somewhere before font-size on the same or nearby line
        # We look for patterns like:
        # .selector_hint { ... font-size: XXrpx; }
        # or grouped selectors .selector_hint, .other { ... font-size: XXrpx; }
        pattern = re.compile(
            r'(' + re.escape(selector_hint) + r'[^}]*?font-size:\s*)' + str(old_val) + r'(rpx)',
            re.DOTALL
        )
        new_content, n = pattern.subn(r'\g<1>' + str(new_val) + r'\2', content)
        if n > 0:
            content = new_content
            changes += n
            print(f"  {target_size_label}: .{selector_hint} {old_val}rpx → {new_val}rpx ({n} occurrence(s))")
    return content, changes

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    total_changes = 0
    relpath = os.path.relpath(filepath, MINIAPP_DIR)
    print(f"\n--- {relpath} ---")
    
    # Apply body upgrades
    content, n = apply_upgrade(content, BODY_UPGRADES, "BODY")
    total_changes += n
    
    # Apply label downgrades (26→24)
    content, n = apply_upgrade(content, LABEL_DOWNGRADES, "LABEL↓")
    total_changes += n
    
    # Apply label upgrades (<24→24)
    content, n = apply_upgrade(content, LABEL_UPGRADES, "LABEL↑")
    total_changes += n
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return total_changes

def main():
    print("=== WXSS Font Size Accessibility Fix ===")
    print("Body/Title/Button: < 28rpx → 28rpx")
    print("Labels/Tips/Aux: < 24rpx → 24rpx; 24rpx stays; some 26rpx labels → 24rpx")
    print()
    
    files = find_wxss_files()
    total = 0
    for f in files:
        n = process_file(f)
        total += n
    
    print(f"\n=== DONE: {total} total changes across {len(files)} files ===")

if __name__ == '__main__':
    main()
