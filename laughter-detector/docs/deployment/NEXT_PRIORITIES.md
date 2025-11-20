# Next Priorities - Post Memory Optimization

## Current Status

**✅ COMPLETED:**
- Memory optimization for multi-user cron jobs
- Bug fix for scheduler._service_client AttributeError
- Comprehensive testing and documentation
- Migration readiness assessment

**Status:** Ready for production deployment on 4GB VPS

---

## Immediate Priorities (Pre-Deployment)

### 1. ✅ Deploy to 4GB VPS
**Priority:** CRITICAL  
**Effort:** 2-4 hours  
**Status:** Ready

**Tasks:**
- [ ] Follow `VPS_MIGRATION_CHECKLIST.md`
- [ ] Deploy code to new 4GB VPS
- [ ] Test with one user first
- [ ] Monitor first cron run
- [ ] Verify memory cleanup working

**Success Criteria:**
- ✅ Cron job runs successfully
- ✅ Memory cleanup working (logs show cleanup)
- ✅ No OOM errors
- ✅ Detections created correctly

---

## Short-Term Priorities (Post-Deployment)

### 2. `/process-current-day` Enhanced Logging
**Priority:** HIGH  
**Effort:** 3-5 hours  
**Status:** Backlogged

**Issue:** Endpoint creates detections without processing logs, making debugging difficult.

**Tasks:**
- [ ] Integrate `enhanced_logger` into endpoint
- [ ] Track audio files downloaded
- [ ] Track laughter events found
- [ ] Track duplicates skipped
- [ ] Save processing log to database

**Documentation:** `docs/backlog/PROCESS_CURRENT_DAY_LOGGING.md`

**Why Important:**
- Enables tracking of manual processing
- Helps debug data inconsistencies
- Provides audit trail
- Matches cron job logging behavior

---

### 3. Production Monitoring Setup
**Priority:** HIGH  
**Effort:** 2-3 hours  
**Status:** Not Started

**Tasks:**
- [ ] Set up log aggregation (if needed)
- [ ] Configure memory alerts (if memory > 1.5 GB after cleanup)
- [ ] Set up OOM kill alerts
- [ ] Create monitoring dashboard (optional)
- [ ] Document monitoring procedures

**Why Important:**
- Early detection of memory leaks
- Proactive OOM prevention
- Production reliability
- Debugging production issues

---

## Medium-Term Priorities

### 4. Retry Logic for 504 Errors
**Priority:** MEDIUM  
**Effort:** 4-6 hours  
**Status:** Backlogged

**Issue:** Limitless API intermittently returns 504 Gateway Timeout errors.

**Tasks:**
- [ ] Implement exponential backoff retry (2-3 attempts)
- [ ] Track retry attempts in logs
- [ ] Handle retry failures gracefully
- [ ] Test with simulated 504 errors

**Documentation:** `docs/features/BACKLOG.md`

**Why Important:**
- Recovers from transient network issues
- Reduces data gaps
- Improves reliability

**When to Implement:**
- If 504 errors are frequent (>10% of requests)
- If users report missing data
- If monitoring shows pattern

---

### 5. Scheduled Orphan Cleanup
**Priority:** MEDIUM  
**Effort:** 2-3 hours  
**Status:** Not Started

**Issue:** Orphaned files can accumulate if processing fails.

**Tasks:**
- [ ] Create scheduled cleanup script
- [ ] Add to cron (daily/weekly)
- [ ] Log cleanup results
- [ ] Alert on excessive orphans

**Why Important:**
- Prevents disk space issues
- Maintains data consistency
- Automated maintenance

---

## Long-Term Priorities

### 6. Additional Memory Optimizations
**Priority:** LOW  
**Effort:** 8-12 hours  
**Status:** Not Needed (Currently)

**Options:**
- Stream processing (process audio in chunks)
- Unload YAMNet model between users
- More aggressive GC settings

**Why Low Priority:**
- Current optimizations sufficient for 4GB VPS
- Peak memory (2.4 GB) is acceptable
- Additional optimizations add complexity
- May slow processing

**When to Consider:**
- If memory issues occur on 4GB VPS
- If processing many users (>5) simultaneously
- If VPS needs to be downsized

---

### 7. Security Enhancements
**Priority:** MEDIUM  
**Effort:** 20+ hours  
**Status:** Backlogged

**Issues:** See `docs/security/SECURITY_PRIORITIES.md`

**High Priority Items:**
- Input validation
- CSRF protection
- Security headers
- CORS configuration

**Why Important:**
- Production security
- User data protection
- Compliance requirements

**When to Implement:**
- Before public launch
- If security audit required
- If handling sensitive data

---

## Backlog Summary

### High Priority
1. ✅ **Deploy to 4GB VPS** (Ready)
2. **`/process-current-day` logging** (3-5 hours)
3. **Production monitoring** (2-3 hours)

### Medium Priority
4. **Retry logic for 504 errors** (4-6 hours, if needed)
5. **Scheduled orphan cleanup** (2-3 hours)
6. **Security enhancements** (20+ hours)

### Low Priority
7. **Additional memory optimizations** (8-12 hours, if needed)

---

## Decision Framework

### When to Prioritize Item

**Deploy to 4GB VPS:**
- ✅ **NOW** - Blocking production deployment

**`/process-current-day` logging:**
- ✅ **After deployment** - Improves debugging, not blocking

**Production monitoring:**
- ✅ **After deployment** - Critical for production reliability

**Retry logic:**
- ⚠️ **If 504 errors frequent** - Monitor first, implement if needed

**Scheduled cleanup:**
- ✅ **After deployment** - Prevents disk issues, low effort

**Memory optimizations:**
- ❌ **Only if needed** - Current optimizations sufficient

**Security enhancements:**
- ⚠️ **Before public launch** - Important but not blocking MVP

---

## Recommended Order

1. **Deploy to 4GB VPS** (Immediate)
2. **Set up production monitoring** (Week 1)
3. **Implement `/process-current-day` logging** (Week 1-2)
4. **Add scheduled orphan cleanup** (Week 2)
5. **Monitor 504 errors** (Week 2-4)
6. **Implement retry logic** (If needed, Week 4+)
7. **Security enhancements** (Before public launch)

---

## Success Metrics

### Deployment Success
- ✅ Cron job runs successfully
- ✅ Memory cleanup working
- ✅ No OOM errors
- ✅ Processing logs created

### Post-Deployment Success
- ✅ Monitoring alerts configured
- ✅ `/process-current-day` logging working
- ✅ Orphan cleanup scheduled
- ✅ 504 error rate < 5%

### Long-Term Success
- ✅ Memory stable over time
- ✅ No production issues
- ✅ Security audit passed
- ✅ Ready for public launch

