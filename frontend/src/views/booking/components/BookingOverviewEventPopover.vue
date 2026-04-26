<template>
  <el-popover trigger="click" placement="right-start" width="300">
    <template #reference>
      <slot />
    </template>

    <div class="booking-popover">
      <div class="popover-title">
        {{ event.booking.booking_no }}
        <el-tag :type="statusTagType" size="small" effect="plain">
          {{ BOOKING_STATUS_MAP[event.booking.booking_status] || event.booking.booking_status }}
        </el-tag>
      </div>
      <ul class="detail-list">
        <li><span>日期</span><strong>{{ event.booking.booking_date }}</strong></li>
        <li><span>時間</span><strong>{{ event.timeLabel }}</strong></li>
        <li><span>老師</span><strong>{{ event.booking.teacher_name || '-' }}</strong></li>
        <li><span>學生</span><strong>{{ event.booking.student_name || '-' }}</strong></li>
        <li><span>課程</span><strong>{{ event.booking.course_name || '-' }}</strong></li>
        <li><span>類型</span><strong>{{ BOOKING_TYPE_MAP[event.booking.booking_type] || event.booking.booking_type || '-' }}</strong></li>
        <li v-if="event.booking.notes" class="is-note">
          <span>備註</span><strong>{{ event.booking.notes }}</strong>
        </li>
      </ul>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { BookingItem, BookingStatus } from '@/api/booking';
import { BOOKING_STATUS_MAP, BOOKING_TYPE_MAP } from '@/constants/booking';

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger' | '';

interface BookingOverviewEvent {
  booking: BookingItem;
  timeLabel: string;
}

const props = defineProps<{
  event: BookingOverviewEvent;
}>();

const statusTagType = computed<TagType>(() => {
  const status = props.event.booking.booking_status as BookingStatus;

  if (status === 'completed') return 'success';
  if (status === 'cancelled') return 'info';
  if (status === 'confirmed') return 'primary';
  if (status === 'pending') return 'warning';
  return '';
});
</script>

<style scoped lang="scss">
.booking-popover {
  .popover-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
    font-weight: 700;
    color: var(--el-text-color-primary);
  }
}

.detail-list {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px dashed var(--el-border-color-lighter);

    &:last-child {
      border-bottom: none;
    }

    span {
      color: var(--el-text-color-secondary);
      font-size: 12px;
    }

    strong {
      min-width: 0;
      color: var(--el-text-color-primary);
      font-size: 12px;
      font-weight: 600;
      overflow-wrap: anywhere;
    }

    &.is-note {
      align-items: flex-start;
    }
  }
}
</style>
