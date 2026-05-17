# Incident Response Runbook — PCC AI Portal

**Owner:** PDE Team + CISO | **Version:** 1.0 | **Ref:** AI Policy v1.0 Section 10

---

## Timeline Summary

| Milestone | Deadline | Owner |
|-----------|----------|-------|
| ตรวจจับ / รับแจ้ง | T+0 | ทุกคน |
| Triage + Contain | T+4h | PDE + CISO |
| Investigate | T+24h | PDE + DPO |
| Fix + KM | T+72h | PDE |
| PDPC Notification (data breach only) | T+72h | DPO |

---

## Step 1 — Detection & Reporting (T+0)

**ช่องทางรับแจ้ง:**
- AI Portal → **Report Incident** button → `POST /incidents`
- Email: `ai-report@precise.co.th`
- ระบบ auto-detect: classifier block Top Secret → auto-create incident

**ข้อมูลที่ต้องกรอก:**
- `category`: data_leak | hallucination | misuse | deepfake | other
- `severity`: low | medium | high | critical
- `title`: สรุปสั้น < 200 ตัวอักษร
- `description`: รายละเอียดเหตุการณ์ (ไม่ต้องระบุเนื้อหาลับ — ระบุบริบทพอ)

**Severity guide:**
- **critical**: data breach ที่อาจกระทบ PDPA, deepfake ผู้บริหาร, system compromise
- **high**: ข้อมูล Confidential รั่วไหล, AI misuse เชิงการเงิน/กฎหมาย
- **medium**: PII ถูกส่งออก, hallucination ใน decision document
- **low**: ใช้ tool ไม่ได้อนุมัติ, prompt engineering พยายาม bypass policy

---

## Step 2 — Triage & Containment (T+4h)

**PDE Actions:**
1. รับ alert ทาง email (`ai-report@precise.co.th`)
2. ตรวจสอบ `audit_logs` + `pii_events` ใน DB
   ```sql
   SELECT al.*, pe.pii_types, pe.action
   FROM audit_logs al
   LEFT JOIN pii_events pe ON pe.user_id = al.user_id
   WHERE al.created_at > NOW() - INTERVAL '24 hours'
   ORDER BY al.created_at DESC;
   ```
3. ถ้า severity = critical:
   - **Block user** ทันที (ผ่าน LiteLLM `/key/block`)
   - แจ้ง CISO + CTO ทันที
4. อัปเดต incident status → `contained`
   ```bash
   PATCH /incidents/{id}  {"status": "contained", "contained_at": "<timestamp>"}
   ```

---

## Step 3 — Investigation (T+24h)

**DPO + PDE Actions:**
1. วิเคราะห์ `audit_logs.classification` + `incidents.description`
2. ระบุ: ข้อมูลอะไร, ใคร, ไปไหน, กระทบใคร
3. ถ้าเป็น data breach → เตรียมเอกสาร PDPC
4. อัปเดต `incidents.investigated_at`

---

## Step 4 — Resolution (T+72h)

1. แก้ไขระบบ (ถ้าจำเป็น)
2. บันทึก `incidents.resolution`
3. อัปเดต KM / SOP
4. ทบทวน AI Policy (ถ้าจำเป็น)
5. อัปเดต status → `resolved`

---

## Step 5 — PDPC Notification (data breach only, T+72h)

ถ้าเข้าเงื่อนไข personal data breach ตาม PDPA:
1. DPO เตรียมแบบฟอร์ม PDPC (ผ่าน pdpc.or.th)
2. ระบุ: ประเภทข้อมูล, จำนวนผู้ได้รับผลกระทบ, มาตรการที่ดำเนินการ
3. บันทึก `incidents.pdpc_notified_at` หลัง submit

---

## Contacts

| บทบาท | ติดต่อ |
|-------|-------|
| Incident Report | ai-report@precise.co.th |
| PDE Team Lead | (ระบุชื่อ) |
| CISO | (ระบุชื่อ) |
| DPO | (ระบุชื่อ) |
| PDPC (external) | pdpc.or.th |

---

## Useful Queries

```sql
-- ดู incidents ที่ยังไม่ resolve
SELECT id, category, severity, title, status, created_at,
       EXTRACT(EPOCH FROM (NOW() - created_at))/3600 AS hours_open
FROM incidents
WHERE status NOT IN ('resolved','closed')
ORDER BY severity DESC, created_at ASC;

-- ดู critical incidents ที่ใกล้ deadline PDPC (72h)
SELECT *, created_at + INTERVAL '72 hours' AS pdpc_deadline
FROM incidents
WHERE severity = 'critical'
  AND category = 'data_leak'
  AND pdpc_notified_at IS NULL;
```
