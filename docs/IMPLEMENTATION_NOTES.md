# Implementation Notes & Gotchas

## Critical Implementation Gotchas

### 1. Units & Rounding
**Status: ✅ IMPLEMENTED CORRECTLY**

- **Current Implementation**: All calculations use feet and cubic yards internally
- **Rounding**: Only applied at presentation layer (e.g., `round(curb_length, 2)` in sitework.py)
- **Units**: Consistent use of `_ft` and `_cy` suffixes throughout depth calculations
- **Conversion**: Proper conversion from SF to CY using `/27.0` factor

**Code Evidence:**
```python
# backend/app/services/detectors/depth.py:216
trench_volume_cy = total_area_sf / 27.0  # Convert SF to CY

# backend/app/services/detectors/sitework.py:35
return round(curb_length, 2)  # Only round at presentation
```

### 2. Stationing Alignment
**Status: ⚠️ NEEDS VERIFICATION**

- **Current Implementation**: Stationing uses normalized 0.0-1.0 range
- **Potential Issue**: No explicit clamping to polyline length
- **Risk**: Station values could exceed actual pipe length

**Required Fix:**
```python
# In sample_depth_along_run function
station = max(0.0, min(1.0, station))  # Clamp to [0, 1]
```

### 3. OD Lookup Fallbacks
**Status: ✅ IMPLEMENTED WITH CONSERVATIVE FALLBACK**

- **Current Implementation**: Uses 1.2x nominal diameter as fallback
- **Warning System**: No explicit warning when material/dia missing
- **Conservative Approach**: Ensures trench CY doesn't vanish

**Code Evidence:**
```python
# backend/app/services/detectors/depth.py:76-77
# Fallback: assume OD is 1.2x nominal diameter
return (dia_in * 1.2) / 12.0
```

**Recommended Enhancement:**
```python
def od_ft(material: str, dia_in: float) -> float:
    # ... existing lookup logic ...
    
    # Fallback with warning
    logger.warning(f"OD lookup failed for {material} {dia_in}in, using conservative fallback")
    return (dia_in * 1.2) / 12.0
```

### 4. Shoring vs Slopes
**Status: ✅ IMPLEMENTED CORRECTLY**

- **Current Implementation**: Clean switching between shoring box and sloped trench
- **Formula**: Proper trapezoidal area calculation
- **Configuration**: Controlled by `use_shoring_box` flag

**Code Evidence:**
```python
# backend/app/services/detectors/depth.py:267-283
def _calculate_trench_area(od_ft, depth_ft, bedding_clearance, side_slope):
    bottom_width = od_ft + (2 * bedding_clearance)
    top_width = bottom_width + (2 * depth_ft * side_slope)
    area = (bottom_width + top_width) / 2 * depth_ft
    return area
```

### 5. Idempotency
**Status: ⚠️ PARTIALLY IMPLEMENTED**

- **Current Implementation**: Uses SHA1 hash for source keys
- **Issue**: Upsert logic in `upsert_counts` is incomplete
- **Missing**: Proper deduplication by (session_id, geom_id, category)

**Current Code:**
```python
# backend/app/services/persistence/review_writer.py:9-11
def _src_key(sheet: Optional[str], geom_id: str, category: str) -> str:
    raw = json.dumps({"sheet": sheet or "", "geom_id": geom_id, "cat": category}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()
```

**Required Fix:**
```python
def upsert_counts(session_id: str, items: List[Dict[str, Any]], db_session):
    for item in items:
        source_ref = item.get("source_ref", {})
        source_key = source_ref.get("hash")
        
        # Proper upsert by (session_id, geom_id, category)
        existing = db_session.query(CountItem).filter(
            CountItem.file == session_id,
            CountItem.type == item["category"],
            CountItem.source_ref["geom_id"] == source_ref["geom_id"]
        ).first()
        
        if existing:
            # Update existing
            existing.attributes = item.get("attributes", {})
            existing.quantity = item.get("quantity", 0)
        else:
            # Create new
            new_item = CountItem(
                file=session_id,
                type=item["category"],
                attributes=item.get("attributes", {}),
                source_ref=source_ref
            )
            db_session.add(new_item)
```

### 6. QA Messages
**Status: ✅ IMPLEMENTED CORRECTLY**

- **Current Implementation**: Numeric and terse messages
- **Format**: "Pipe cover 2.1ft < required 3.0ft"
- **Display**: Suitable for badges and tooltips

**Code Evidence:**
```python
# backend/app/services/detectors/qa_rules.py:68
message=f"Sewer pipe cover {min_depth_ft:.1f}ft < required {min_cover_ft}ft"
```

## Additional Implementation Notes

### Database Migrations
- **Indices**: Properly created for performance optimization
- **Constraints**: Missing unique constraints for idempotency
- **Recommendation**: Add unique constraint on (file, type, source_ref->geom_id)

### Security Middleware
- **Request Size**: 10MB default limit
- **Rate Limiting**: 100/hour, 100/minute defaults
- **Headers**: Security headers properly set

### Demo Mode
- **Session Management**: Proper cleanup and limits
- **Sample Files**: Placeholder files created
- **Banner**: Frontend component with limits display

## Recommended Fixes

### 1. Station Clamping
```python
# In sample_depth_along_run
station = max(0.0, min(1.0, station))  # Clamp to [0, 1]
```

### 2. OD Lookup Warnings
```python
def od_ft(material: str, dia_in: float) -> float:
    # ... existing logic ...
    logger.warning(f"OD lookup failed for {material} {dia_in}in, using conservative fallback")
    return (dia_in * 1.2) / 12.0
```

### 3. Proper Idempotency
```python
def upsert_counts(session_id: str, items: List[Dict[str, Any]], db_session):
    for item in items:
        source_ref = item.get("source_ref", {})
        geom_id = source_ref.get("geom_id")
        category = item["category"]
        
        existing = db_session.query(CountItem).filter(
            CountItem.file == session_id,
            CountItem.type == category,
            CountItem.source_ref["geom_id"] == geom_id
        ).first()
        
        if existing:
            # Update existing item
            existing.attributes = item.get("attributes", {})
            existing.quantity = item.get("quantity", 0)
        else:
            # Create new item
            new_item = CountItem(
                file=session_id,
                type=category,
                attributes=item.get("attributes", {}),
                source_ref=source_ref
            )
            db_session.add(new_item)
    
    db_session.commit()
```

### 4. Database Schema Enhancement
```sql
-- Add unique constraint for idempotency
ALTER TABLE countitem ADD CONSTRAINT uq_countitem_source 
UNIQUE (file, type, json_extract(source_ref, '$.geom_id'));
```

## Testing Recommendations

### 1. Unit Tests
- Test station clamping with edge cases (0.0, 1.0, negative, >1.0)
- Test OD lookup fallbacks with missing materials
- Test idempotency with duplicate submissions
- Test QA message formatting

### 2. Integration Tests
- Test complete depth calculation pipeline
- Test review commit idempotency
- Test demo mode limits and cleanup

### 3. Performance Tests
- Test database query performance with indices
- Test rate limiting under load
- Test memory usage with large files

## Conclusion

The implementation is largely correct with a few critical areas needing attention:

1. **Station clamping** - Add explicit bounds checking
2. **Idempotency** - Fix upsert logic for proper deduplication  
3. **OD warnings** - Add logging for missing lookup data
4. **Database constraints** - Add unique constraints for idempotency

These fixes will ensure robust, production-ready depth and trench calculations with proper error handling and data integrity.
