# Backlog — digilio-v2

Catatan task yang ditunda / belum dieksekusi. Item dipindah ke sini saat user minta
"masukkan ke backlog". Kerjakan saat diminta.

## Open

- [ ] **Soft-delete cascade untuk lines/children** — saat parent di-delete (soft_delete),
      lines one2many-nya ikut terhapus (mis. `project.milestone` → `project.milestone_line`).
      Saat ini `soft_delete()` di `core/model_meta.py` hanya menandai parent; children
      menjadi orphan (berlaku untuk semua model, termasuk PO lines). Perlu override
      generik atau penanganan di `model_api.py` delete handler.

## Done

_(kosong)_
