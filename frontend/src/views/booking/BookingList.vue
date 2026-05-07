<template>
  <div class="booking-list pl-2 pr-4">
    <!-- Quick Batch Actions Top -->
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="text-lg my-0">{{ $t('menu.booking_mgmt') }}</h3>
      <div class="flex gap-1">
        <el-button
          v-if="hasPermission('bookings.create')"
          type="success" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchCreate')">
            <template #icon><div class="i-hugeicons:add-circle" /></template>
            {{ $t('bookingAdmin.batchCreate') }}
        </el-button>
        <el-button
          v-if="hasPermission('bookings.edit')"
          type="warning" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchUpdate')">
            <template #icon><div class="i-hugeicons:edit-02" /></template>
            {{ $t('bookingAdmin.batchUpdate') }}
        </el-button>
        <el-button
          v-if="hasPermission('bookings.edit')"
          type="danger" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchDelete')">
            <template #icon><div class="i-hugeicons:delete-02" /></template>
            {{ $t('bookingAdmin.batchDelete') }}
        </el-button>
        <el-button
          v-if="hasPermission('bookings.create')"
          type="primary"
          round
          size="small"
          class="h-30px px-2"
          @click="openDialog('add')"
        >
          <template #icon>
            <div class="i-hugeicons:plus-sign-square" />
          </template>
          {{ $t('booking.add') }}
        </el-button>
      </div>
    </div>

    <!-- Filter Bar -->
    <el-card shadow="never" class="mb-4">
      <el-form 
        :inline="true" 
        :model="filters" 
        size="small" 
        label-position="top" 
        class="filter-form flex flex-wrap items-end">
        <el-form-item :label="$t('bookingAdmin.keyword')">
          <el-input 
            v-model="filters.search" 
            :placeholder="$t('bookingAdmin.keywordPlaceholder')"
            clearable 
            class="h-30px! w-200px!" 
            @clear="handleFilterChange" 
            @keyup.enter="handleFilterChange">
            <template #prefix><div class="i-hugeicons:search-01" /></template>
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('common.dateRange')">
          <el-date-picker 
            v-model="filters.dateRange" 
            type="daterange" 
            range-separator="~" 
            :start-placeholder="$t('common.startDate')" 
            :end-placeholder="$t('common.endDate')" 
            class="w-240px! h-30px!" 
            clearable 
            @change="handleFilterChange" 
          />
        </el-form-item>
        <el-form-item :label="$t('common.status')">
          <el-select 
            v-model="filters.status" 
            :placeholder="$t('common.all')" 
            clearable 
            class="w-110px!" 
            @change="handleFilterChange">
            <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.teacher')">
          <el-select 
            v-model="filters.teacherId" 
            :placeholder="$t('common.all')" 
            clearable 
            filterable 
            class="w-140px!" 
            @change="handleFilterChange">
            <el-option v-for="t in teacherOptions" :key="t.id" :label="`${t.teacher_no} - ${t.name}`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.student')">
          <el-select 
            v-model="filters.studentId" 
            :placeholder="$t('common.all')" 
            clearable 
            filterable 
            class="w-140px!" 
            @change="handleFilterChange">
            <el-option v-for="s in studentOptions" :key="s.id" :label="`${s.student_no} - ${s.name}`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('bookingAdmin.courseFilter')">
          <el-select v-model="filters.courseId" :placeholder="$t('common.all')" clearable filterable class="w-160px!" @change="handleFilterChange">
            <el-option v-for="c in courseOptions" :key="c.id" :label="`${c.course_code} - ${c.course_name}`" :value="c.id" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round size="small" class="h-30px!" @click="handleFilterChange">
            <template #icon><div class="i-hugeicons:search-01" /></template>{{ $t('common.search') }}
          </el-button>
          <el-button round size="small" class="h-30px!" @click="handleReset">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>{{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table Toolbar -->
    <div class="mb-2">
      <el-button
        v-if="hasPermission('bookings.edit')"
        type="warning"
        round
        size="small"
        plain 
        class="h-30px!"
        :disabled="selectedIds.length === 0" 
        @click="openDialog('batchUpdateByIds')">
        <template #icon><div class="i-hugeicons:edit-02" /></template>
        {{ $t('bookingAdmin.batchUpdateStatus') }}
      </el-button>
      <el-button
        v-if="hasPermission('bookings.edit')"
        type="danger" 
        plain 
        round
        size="small"
        class="h-30px!"
        :disabled="selectedIds.length === 0" 
        @click="handleBatchDeleteByIds">
        <template #icon><div class="i-hugeicons:delete-02" /></template>
        {{ $t('bookingAdmin.batchDelete') }}
      </el-button>
    </div>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="tableData" style="width: 100%" v-loading="loading" stripe size="small" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="40" align="center" fixed="left" />
        <el-table-column :label="$t('bookingAdmin.bookingNo')" prop="booking_no" width="200">
          <template #default="{ row }">
            <div class="flex justify-between items-center gap-2 pr-3">
              <div class="font-bold">{{ row.booking_no }}</div>
              <el-tag 
                :type="row.booking_type === 'trial' ? 'warning' : ''" 
                effect="plain" 
                size="small"
                class="h-20px! text-10px! px-1!">
                {{ row.booking_type === 'trial' || row.booking_type === 'regular' ? $t(`bookingShared.type.${row.booking_type}`) : row.booking_type }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.student')" min-width="140">
          <template #default="{ row }">{{ row.student_name || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('common.teacher')" min-width="140">
          <template #default="{ row }">
            <div>{{ row.teacher_name || '-' }}</div>
            <div v-if="row.substitute_teacher_name" class="text-xs color-gray-500 mt-1">
              {{ $t('bookingAdmin.substituteTeacher', { name: row.substitute_teacher_name }) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.course')" min-width="180">
          <template #default="{ row }">{{ row.course_name || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('salary.dateTime')" min-width="120">
          <template #default="{ row }">
            {{ row.booking_date }}<br>
            <span class="text-xs color-gray-500">
              {{ row.start_time ? row.start_time.substring(0, 5) : '' }} ~ {{ row.end_time ? row.end_time.substring(0, 5) : '' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.status')" min-width="120" align="center">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusColor(row.booking_status)" 
              size="small"
              class="text-11px! bg-transparent!">
              <div class="flex items-center gap-1">
                <span :class="`text-sm color-${getStatusColor(row.booking_status)}`">•</span>
                <span>{{ $t(`bookingShared.status.${row.booking_status}`) }}</span>
              </div>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('bookingAdmin.zoomColumn')" min-width="160" align="center">
          <template #default="{ row }">
            <template v-if="['pending', 'confirmed', 'completed'].includes(row.booking_status)">
              <div v-if="!zoomInfoMap[row.id]" class="flex justify-center items-center min-h-12">
                <el-button 
                  v-if="hasPermission('bookings.edit')"
                  type="primary" 
                  size="small" 
                  plain
                  round
                  class="text-xs h-20px! px-1.5!"
                  :loading="creatingZoomMap[row.id]"
                  @click="handleCreateZoom(row)">
                  <template #icon><div class="i-hugeicons:meeting-room" /></template>
                  {{ $t('bookingAdmin.createMeeting') }}
                </el-button>
              </div>
              <div v-else class="flex flex-col items-center gap-2 min-h-12 justify-center">
                <div class="flex flex-col justify-center items-center gap-1"> 
                  <el-button 
                    v-if="zoomInfoMap[row.id]?.join_url"
                    type="success" 
                    size="small"
                    round
                    plain
                    class="text-xs h-20px! px-1.5!"
                    @click="openUrl(zoomInfoMap[row.id]?.join_url)">
                    <template #icon><div class="i-hugeicons:video-01" /></template>{{ $t('bookingAdmin.joinMeeting') }}
                  </el-button>
                  <div 
                    v-if="zoomInfoMap[row.id]?.passcode" 
                    class="flex items-center gap-0.5 text-11px leading-12px color-gray-400 translate-x-10px">
                    {{ $t('bookingAdmin.passcode', { passcode: zoomInfoMap[row.id]?.passcode }) }}
                    <el-button size="small" round link class="text-xs h-20px! px-1! color-gray-400! hover:color-gray-500!" @click="copyToClipboard(zoomInfoMap[row.id]?.passcode)"><div class="i-hugeicons:copy-01" /></el-button>
                </div>
                </div>
                <el-button 
                  v-if="zoomInfoMap[row.id]?.drive_view_link || zoomInfoMap[row.id]?.recording_url"
                  type="info" 
                  size="small" 
                  round
                  plain
                  class="text-xs h-20px! px-1.5!"
                  @click="openUrl(zoomInfoMap[row.id]?.drive_view_link || zoomInfoMap[row.id]?.recording_url)">
                  <template #icon><div class="i-hugeicons:video-replay" /></template>{{ $t('bookingAdmin.viewRecording') }}
                </el-button>
              </div>
            </template>
            <div v-else class="flex justify-center items-center min-h-12">
              <span class="text-gray-400">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" min-width="240" align="center" fixed="right">
          <template #default="{ row }">
              <div class="flex flex-col justify-between gap-2 items-start px-1">
              <div>
                <el-button v-if="hasPermission('bookings.edit')" link type="primary" size="small" @click="openDialog('edit', row)">{{ $t('common.edit') }}</el-button>
                <el-button v-if="hasPermission('bookings.edit')" link type="danger" size="small" @click="handleDelete(row)">
                  <template #icon><div class="i-hugeicons:delete-02" /></template>
                  {{ $t('common.delete') }}
                </el-button>
              </div>
              <template v-if="row.booking_status === 'confirmed'">
                <div class="flex justify-center gap-2 mt-2">
                  <div v-if="hasPermission('bookings.list')">
                    <el-button
                      plain
                      type="primary"
                      size="small"
                      round
                      :disabled="Boolean(row.has_pending_leave)"
                      @click="openLeaveDialog(row)">
                      {{ $t('teacherRecords.btnLeave') }}
                    </el-button>
                  </div>
                  <div v-if="hasPermission('bookings.edit')">
                    <el-button
                    v-if="!row.substitute_detail_id"
                    plain
                    type="primary"
                    size="small"
                    round
                    @click="openSubstituteDialog(row)">
                    {{ $t('bookingAdmin.substituteAction') }}
                  </el-button>
                  <el-button
                    v-else
                    plain
                    type="danger"
                    size="small"
                    round
                    @click="handleCancelSubstitute(row)">
                    {{ $t('bookingAdmin.cancelSubstitute') }}
                  </el-button>
                  </div>
                  <div v-if="hasPermission('bookings.edit')">
                    <el-button plain type="danger" size="small" round @click="handleCancelBooking(row)">
                      {{ $t('bookingAdmin.cancelBooking') }}
                    </el-button>
                  </div>
              </div>
            </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination 
          v-model:current-page="currentPage" 
          v-model:page-size="pageSize" 
          :page-sizes="[10, 20, 50, 100]" 
          layout="total, sizes, prev, pager, next, jumper" 
          :total="total" 
          @current-change="handlePaginationChange" 
          @size-change="handleFilterChange" 
        />
      </div>
    </el-card>

    <!-- Generic Dialog -> Standard Add Booking -->
    <el-drawer v-model="dialogs.add.visible" :title="$t('booking.add')" size="480px" @closed="resetForm('add')">
        <el-form :model="addForm" :rules="addRules" ref="addFormRef" size="small" label-width="80px" label-position="top">
          <el-row>
            <el-col :span="10">

              <el-form-item :label="$t('common.student')" prop="student_id">
                  <el-select v-model="addForm.student_id" filterable :placeholder="$t('bookingAdmin.selectStudentFirst')" class="w-full" @change="handleAddStudentChange">
                      <el-option v-for="s in studentOptions" :key="s.id" :label="`${s.student_no} - ${s.name}`" :value="s.id" />
                  </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="10" :push="2">
              <el-form-item :label="$t('bookingAdmin.studentContractOptional')" prop="student_contract_id">
                  <el-select 
                    v-model="addForm.student_contract_id" 
                    filterable 
                    clearable 
                    :placeholder="$t('bookingAdmin.selectContract')"
                    class="w-full" 
                    :disabled="!addForm.student_id" 
                    :loading="addDeps.isFetchingTeachers">
                      <el-option 
                        v-for="c in addDeps.studentContractOptions" 
                        :key="c.id" 
                        :label="`${c.contract_no}${c.course_name ? (' - ' + c.course_name) : ''}`" 
                        :value="c.id" />
                  </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="10">
              <el-form-item :label="$t('common.teacher')" prop="teacher_id">
                <el-select 
                  v-model="addForm.teacher_id" 
                  filterable 
                  :placeholder="$t('bookingAdmin.selectTeacher')"
                  class="w-full" 
                  :disabled="!addForm.student_id" 
                  @change="handleAddTeacherChange"
                  :loading="addDeps.isFetchingTeachers">
                    <el-option v-for="t in addDeps.teacherOptions" :key="t.id" :label="formatTeacherOptionLabel(t)" :value="t.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="10" :push="2">
              <el-form-item :label="$t('common.course')" prop="course_id">
                <el-select 
                  v-model="addForm.course_id" 
                  filterable 
                  :placeholder="$t('bookingAdmin.selectCourse')"
                  class="w-full" 
                  :disabled="!addForm.student_id || !addForm.teacher_id" 
                  :loading="addDeps.isFetchingCourses">
                    <el-option v-for="c in addDeps.courseOptions" :key="c.id" :label="formatCourseOptionLabel(c)" :value="c.id" />
                </el-select>
                <div
                  v-if="addForm.student_id && addForm.teacher_id && !addDeps.isFetchingCourses && addDeps.courseOptions.length === 0"
                  class="mt-1 text-xs color-[#f56c6c]">
                  {{ $t('bookingAdmin.noSharedCourses') }}
                </div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="16">
              <el-form-item :label="$t('bookingAdmin.timeMode')">
                <el-radio-group v-model="addForm.timeMode" :disabled="!addForm.teacher_id" @change="handleAddTimeModeChange">
                  <el-radio label="manual">{{ $t('bookingAdmin.manualTime') }}</el-radio>
                  <el-radio label="slot">{{ $t('bookingAdmin.teacherSlot') }}</el-radio>
                </el-radio-group>
            </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="16">
            <!-- Manual Mode -->
            <template v-if="addForm.timeMode === 'manual'">
              <el-form-item :label="$t('bookingAdmin.date')" prop="booking_date">
                <el-date-picker
                  v-model="addForm.booking_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :placeholder="$t('bookingAdmin.selectDate')"
                  class="w-full h-30px!"
                  :disabled="!addForm.teacher_id" />
              </el-form-item>
              <el-form-item :label="$t('bookingAdmin.time')" required>
                <div class="flex gap-2 w-full">
                  <el-time-picker
                    v-model="addForm.start_time"
                    format="HH:mm"
                    value-format="HH:mm"
                    :placeholder="$t('bookingAdmin.start')"
                    class="flex-1 h-30px!" />
                  <span class="mt-1">-</span>
                  <el-time-picker
                    v-model="addForm.end_time"
                    format="HH:mm"
                    value-format="HH:mm"
                    :placeholder="$t('bookingAdmin.end')"
                    class="flex-1 h-30px!" />
                </div>
              </el-form-item>
            </template>
            </el-col>
            <el-col :span="24">
              <!-- Slot Mode -->
              <template v-if="addForm.timeMode === 'slot'">
                <el-form-item :label="$t('bookingAdmin.teacherSlotLabel')" prop="teacher_slot_id">
                  <el-select 
                    v-model="addForm.teacher_slot_id" 
                    :placeholder="$t('bookingAdmin.selectTeacherSlot')"
                    class="w-220px"
                    @change="handleTeacherSlotChange"
                    :loading="addDeps.isFetchingCourses">
                    <template #label="{ label }">
                      <div class="flex gap-2">
                        <span class="font-500 w-85px">{{ label.split(' ')[0] }}</span>
                        <span class="font-500">{{ label.split(' ')[1] }}</span>
                      </div>
                    </template>
                    <el-option 
                      v-for="slot in addDeps.teacherSlotOptions" 
                      :key="slot.id" 
                      :value="slot.id" 
                      :label="`${dayjs(slot.slot_date).format('YYYY/MM/DD')} ${slot.start_time.substring(0,5)}~${slot.end_time.substring(0,5)}`"
                    >
                      <div class="flex gap-2">
                        <span class="font-500 w-85px">{{ dayjs(slot.slot_date).format('YYYY/MM/DD') }}</span>
                        <span class="font-500">{{ slot.start_time.substring(0,5)}}~{{ slot.end_time.substring(0,5)}}</span>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
                <el-form-item
                  v-if="addForm.teacher_slot_id"
                  v-loading="slotAvailabilityLoading"
                  prop="slot_block_time">
                  <template #label>
                    <span>{{ $t('bookingAdmin.availableTimeBlocks') }}</span>
                    <span class="ml-2 text-xs color-[#909399]">{{ $t('bookingAdmin.slotRangeHint') }}</span>
                  </template>
                  <div v-if="slotAvailability?.blocks?.length" class="flex flex-wrap gap-2">
                    <div class="mt-1" v-for="block in slotAvailability.blocks" :key="`${block.start_time}-${block.end_time}`">
                      <el-button
                        size="small"
                        class="w-80px h-60px p-2! rounded-8px"
                        :class="{ 'shadow-[inset_0_0_0_2px_#3695ff]': isSlotStartAndEndBlock(block) }"
                        :type="isSelectedSlotBlock(block) ? 'primary' : 'default'"
                        :disabled="!block.is_available"
                        @click="selectSlotBlock(block)">
                        <div
                          class="flex flex-col items-center gap-0.5 leading-tight"
                        >
                          <span>{{ formatSlotBlockTime(block) }}</span>
                          <span
                            v-if="getSlotBlockSelectionText(block)"
                            class="text-10px opacity-80"
                            :class="{ 'slot-block-start-end': isSlotStartAndEndBlock(block) }"
                          >
                            {{ getSlotBlockSelectionText(block) }}
                          </span>
                          <span v-if="!block.is_available" class="mt-0.5 text-10px">{{ $t('bookingAdmin.slotAlreadyBooked') }}</span>
                        </div>
                      </el-button>
                    </div>
                  </div>
                  <div v-else-if="!slotAvailabilityLoading" class="text-xs color-[#f56c6c]">
                    {{ $t('bookingAdmin.noAvailableTimeBlocks') }}
                  </div>
                </el-form-item>
              </template>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="23">
              <el-form-item :label="$t('common.note')" prop="notes">
                  <el-input v-model="addForm.notes" type="textarea" :rows="4" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <template #footer>
            <el-button size="small" round class="h-30px! px-4!" @click="dialogs.add.visible = false">{{ $t('common.cancel') }}</el-button>
            <el-button size="small" type="primary" round class="h-30px! px-4!" @click="submitAdd" :loading="dialogs.add.loading">{{ $t('bookingAdmin.add') }}</el-button>
        </template>
    </el-drawer>

    <!-- Single Edit Booking -->
    <el-drawer v-model="dialogs.edit.visible" :title="$t('booking.editTitle')" size="480px" @closed="resetForm('edit')">
      <div class="mb-8 p-4 bg-gray-100 rounded-md">
        <div class="font-500 mb-4 text-xs color-[#3f4254]">{{ $t('bookingAdmin.bookingInfo') }}</div>
        <div class="flex flex-col gap-2 text-xs">
          <div><label class="color-[#7e8299] mr-2">{{ $t('common.student') }}</label><span class="color-[#3f4254]">{{ editForm?.student_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">{{ $t('common.teacher') }}</label><span class="color-[#3f4254]">{{ editForm?.teacher_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">{{ $t('common.course') }}</label><span class="color-[#3f4254]">{{ editForm?.course_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">{{ $t('common.date') }}</label><span class="color-[#3f4254]">{{ editForm?.booking_date || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">{{ $t('common.time') }}</label><span class="color-[#3f4254]">{{ editForm?.start_time || '-' }} - {{ editForm?.end_time || '-' }}</span></div>
        </div>
      </div>
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" size="small" label-width="72px" label-position="top">
          <el-form-item :label="$t('common.status')" prop="booking_status">
            <el-select v-model="editForm.booking_status" class="w-150px">
              <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('bookingAdmin.endTime')" prop="end_time">
            <el-time-picker 
              v-model="editForm.end_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              :placeholder="$t('bookingAdmin.endTimePlaceholder')"
              class="w-150px! h-30px!" />
            <div class="text-xs text-gray-400 ml-4">{{ $t('bookingAdmin.endTimeHint') }}</div>
          </el-form-item>
          <el-form-item :label="$t('common.note')" prop="notes">
            <el-input v-model="editForm.notes" type="textarea" :rows="4" />
          </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" round class="h-30px! px-4!" @click="dialogs.edit.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" round class="h-30px! px-4!" @click="submitEdit" :loading="dialogs.edit.loading">{{ $t('bookingAdmin.update') }}</el-button>
      </template>
    </el-drawer>

    <!-- Batch Update By Ids -->
    <el-dialog 
      v-model="dialogs.batchUpdateByIds.visible" 
      :title="$t('bookingAdmin.batchUpdateStatus')"
      width="400px" 
      @closed="resetForm('batchUpdateByIds')">
      <el-form 
        :model="batchUpdateByIdsForm" 
        ref="batchUpdateByIdsRef" 
        label-width="80px">
          <el-form-item :label="$t('bookingAdmin.newStatus')">
            <el-select v-model="batchUpdateByIdsForm.booking_status" class="w-full">
              <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.note')">
            <el-input v-model="batchUpdateByIdsForm.notes" type="textarea" />
          </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.batchUpdateByIds.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button 
          type="primary" 
          @click="submitBatchUpdateByIds" 
          :loading="dialogs.batchUpdateByIds.loading">{{ $t('bookingAdmin.update') }}</el-button>
      </template>
    </el-dialog>

    <!-- Periodic Batch Create -->
    <el-dialog 
      v-model="dialogs.batchCreate.visible" 
      :title="$t('bookingAdmin.batchCreate')"
      width="520px" 
      @closed="resetForm('batchCreate')">
      <el-form :model="batchCreateForm" :rules="batchCreateRules" ref="batchCreateRef" label-width="120px" class="p-2">
        <el-form-item :label="$t('common.student')" prop="student_id">
            <el-select v-model="batchCreateForm.student_id" filterable :placeholder="$t('bookingAdmin.selectStudentFirst')" class="w-full" @change="batchCreateDeps.handleStudentChange()">
              <el-option v-for="s in studentOptions" :key="s.id" :label="`${s.student_no} - ${s.name}`" :value="s.id" />
            </el-select>
        </el-form-item>
        <el-form-item :label="$t('bookingAdmin.studentContractOptional')" prop="student_contract_id">
            <el-select v-model="batchCreateForm.student_contract_id" filterable clearable :placeholder="$t('bookingAdmin.selectContract')" class="w-full" :disabled="!batchCreateForm.student_id" :loading="batchCreateDeps.isFetchingTeachers">
              <el-option v-for="c in batchCreateDeps.studentContractOptions" :key="c.id" :label="`${c.course_name || ''} (${c.contract_no})`" :value="c.id" />
            </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.teacher')" prop="teacher_id">
            <el-select v-model="batchCreateForm.teacher_id" filterable :placeholder="$t('bookingAdmin.selectTeacher')" class="w-full" :disabled="!batchCreateForm.student_id" @change="batchCreateDeps.handleTeacherChange(false)" :loading="batchCreateDeps.isFetchingTeachers">
              <el-option v-for="t in batchCreateDeps.teacherOptions" :key="t.id" :label="`${t.teacher_no} - ${t.name}`" :value="t.id" />
            </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.course')" prop="course_id">
            <el-select v-model="batchCreateForm.course_id" filterable :placeholder="$t('bookingAdmin.selectCourse')" class="w-full" :disabled="!batchCreateForm.student_id || !batchCreateForm.teacher_id" :loading="batchCreateDeps.isFetchingCourses">
              <el-option v-for="c in batchCreateDeps.courseOptions" :key="c.id" :label="`${c.course_code} - ${c.course_name}`" :value="c.id" />
            </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.dateRange')" required>
          <el-date-picker 
            v-model="batchCreateForm.daterange" 
            type="daterange" 
            value-format="YYYY-MM-DD" 
            class="w-full!" />
        </el-form-item>
        <el-form-item :label="$t('bookingAdmin.classTime')">
          <div class="flex gap-2 w-full">
            <el-time-picker 
              v-model="batchCreateForm.start_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              :placeholder="$t('bookingAdmin.start')"
              class="flex-1" />
            <span class="mt-1">-</span>
            <el-time-picker 
              v-model="batchCreateForm.end_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              :placeholder="$t('bookingAdmin.end')"
              class="flex-1" />
          </div>
        </el-form-item>
        <el-form-item :label="$t('bookingAdmin.weekday')">
          <el-checkbox-group v-model="batchCreateForm.weekdays">
            <el-checkbox v-for="option in weekdayOptionsLong" :key="option.value" :label="option.value" class="mr-6">{{ option.label }}</el-checkbox>
          </el-checkbox-group>
          <div class="text-xs text-gray-400 w-full mt-1">{{ $t('bookingAdmin.weekdayBlankAll') }}</div>
        </el-form-item>
        <el-form-item :label="$t('common.note')">
          <el-input v-model="batchCreateForm.notes" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.batchCreate.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button 
          type="primary" 
          @click="submitBatchCreate" 
          :loading="dialogs.batchCreate.loading">{{ $t('bookingAdmin.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- Periodic Batch Update -->
    <el-dialog 
      v-model="dialogs.batchUpdate.visible" 
      :title="$t('bookingAdmin.batchUpdateSchedule')"
      width="520px" 
      @closed="resetForm('batchUpdate')">
        <el-form :model="batchUpdateForm" :rules="batchUpdateRules" ref="batchUpdateRef" label-width="120px" class="p-2">
          <div class="font-bold mb-3 border-b pb-2">{{ $t('bookingAdmin.filterSection') }}</div>
          <el-form-item :label="$t('common.dateRange')" required>
            <el-date-picker 
              v-model="batchUpdateForm.daterange" 
              type="daterange" 
              value-format="YYYY-MM-DD" 
              class="w-full!" />
          </el-form-item>
          <el-form-item :label="$t('bookingAdmin.weekday')">
            <el-checkbox-group v-model="batchUpdateForm.weekdays">
              <el-checkbox v-for="option in weekdayOptionsShort" :key="option.value" :label="option.value">{{ option.label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item :label="$t('common.student')">
            <el-select 
              v-model="batchUpdateForm.student_id" 
              filterable 
              clearable 
              :placeholder="$t('bookingAdmin.selectStudentFirst')"
              class="w-full" 
              @change="batchUpdateDeps.handleStudentChange()">
              <el-option 
                v-for="s in studentOptions" 
                :key="s.id" 
                :label="`${s.student_no} - ${s.name}`" 
                :value="s.id"/>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.teacher')">
            <el-select 
              v-model="batchUpdateForm.teacher_id" 
              filterable 
              clearable 
              :placeholder="$t('bookingAdmin.selectTeacher')"
              class="w-full" 
              :disabled="!batchUpdateForm.student_id" 
              @change="batchUpdateDeps.handleTeacherChange(false)" 
              :loading="batchUpdateDeps.isFetchingTeachers">
              <el-option 
                v-for="t in batchUpdateDeps.teacherOptions" 
                :key="t.id" 
                :label="`${t.teacher_no} - ${t.name}`" 
                :value="t.id"/>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.course')">
            <el-select 
              v-model="batchUpdateForm.course_id" 
              filterable 
              clearable 
              :placeholder="$t('bookingAdmin.selectCourse')"
              class="w-full" 
              :disabled="!batchUpdateForm.student_id || !batchUpdateForm.teacher_id" 
              :loading="batchUpdateDeps.isFetchingCourses">
              <el-option 
                v-for="c in batchUpdateDeps.courseOptions" 
                :key="c.id" 
                :label="`${c.course_code} - ${c.course_name}`" 
                :value="c.id"/>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('bookingAdmin.originalStatus')">
            <el-select 
              v-model="batchUpdateForm.filter_status" 
              clearable 
              class="w-full">
              <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>

          <div class="font-bold mb-3 mt-5 border-b pb-2">{{ $t('bookingAdmin.updateSection') }}</div>
          <el-form-item :label="$t('bookingAdmin.newStatus')" prop="new_status">
            <el-select 
              v-model="batchUpdateForm.new_status" 
              class="w-full">
              <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.note')">
            <el-input v-model="batchUpdateForm.notes" type="textarea" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogs.batchUpdate.visible = false">{{ $t('common.cancel') }}</el-button>
          <el-button 
            type="primary" 
            @click="submitBatchUpdate" 
            :loading="dialogs.batchUpdate.loading">{{ $t('bookingAdmin.update') }}</el-button>
        </template>
    </el-dialog>

    <!-- Periodic Batch Delete -->
    <el-dialog 
      v-model="dialogs.batchDelete.visible" 
      :title="$t('bookingAdmin.batchDeleteSchedule')"
      width="520px" 
      @closed="resetForm('batchDelete')">
        <el-form :model="batchDeleteForm" :rules="batchDeleteRules" ref="batchDeleteRef" label-width="120px" class="p-2">
          <el-form-item :label="$t('common.dateRange')" required>
              <el-date-picker 
                v-model="batchDeleteForm.daterange" 
                type="daterange" 
                value-format="YYYY-MM-DD" 
                class="w-full!" />
          </el-form-item>
          <el-form-item :label="$t('bookingAdmin.weekday')">
              <el-checkbox-group v-model="batchDeleteForm.weekdays">
                  <el-checkbox v-for="option in weekdayOptionsShort" :key="option.value" :label="option.value">{{ option.label }}</el-checkbox>
              </el-checkbox-group>
          </el-form-item>
          <el-form-item :label="$t('common.student')">
              <el-select 
                v-model="batchDeleteForm.student_id" 
                filterable 
                clearable 
                :placeholder="$t('bookingAdmin.selectStudentFirst')"
                class="w-full" 
                @change="batchDeleteDeps.handleStudentChange()">
                <el-option 
                  v-for="s in studentOptions" 
                  :key="s.id" 
                  :label="`${s.student_no} - ${s.name}`" 
                  :value="s.id"/>
              </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.teacher')">
              <el-select 
                v-model="batchDeleteForm.teacher_id" 
                filterable 
                clearable 
                :placeholder="$t('bookingAdmin.selectTeacher')"
                class="w-full" 
                :disabled="!batchDeleteForm.student_id" 
                @change="batchDeleteDeps.handleTeacherChange(false)" 
                :loading="batchDeleteDeps.isFetchingTeachers">
                <el-option 
                  v-for="t in batchDeleteDeps.teacherOptions" 
                  :key="t.id" 
                  :label="`${t.teacher_no} - ${t.name}`" 
                  :value="t.id"/>
              </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.course')">
              <el-select 
                v-model="batchDeleteForm.course_id" 
                filterable 
                clearable 
                :placeholder="$t('bookingAdmin.selectCourse')"
                class="w-full" 
                :disabled="!batchDeleteForm.student_id || !batchDeleteForm.teacher_id" 
                :loading="batchDeleteDeps.isFetchingCourses">
                <el-option 
                  v-for="c in batchDeleteDeps.courseOptions" 
                  :key="c.id" 
                  :label="`${c.course_code} - ${c.course_name}`" 
                  :value="c.id"/>
              </el-select>
          </el-form-item>
          <el-form-item :label="$t('common.status')">
              <el-select 
                v-model="batchDeleteForm.filter_status" 
                clearable 
                class="w-full">
                <el-option v-for="option in bookingStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogs.batchDelete.visible = false">{{ $t('common.cancel') }}</el-button>
          <el-button 
            type="danger" 
            @click="submitBatchDelete" 
            :loading="dialogs.batchDelete.loading">{{ $t('common.delete') }}</el-button>
        </template>
    </el-dialog>

    <el-dialog
      v-model="leaveDialogVisible"
      :title="$t('bookingAdmin.leaveRequestTitle')"
      width="460px"
      destroy-on-close
      @closed="resetLeaveForm">
      <div v-if="leaveBooking" class="mb-4 rounded-md bg-gray-50 p-4 text-sm">
        <div class="mb-1 font-500">{{ leaveBooking.booking_no }}</div>
        <div class="text-xs color-gray-500">
          {{ leaveBooking.booking_date }} {{ leaveBooking.start_time?.substring(0, 5) }}~{{ leaveBooking.end_time?.substring(0, 5) }}
        </div>
        <div class="mt-1 text-xs color-gray-500">
          {{ leaveBooking.student_name || '-' }} / {{ leaveBooking.teacher_name || '-' }} / {{ leaveBooking.course_name || '-' }}
        </div>
      </div>

      <el-form ref="leaveFormRef" :model="leaveForm" :rules="leaveRules" label-position="top">
        <el-form-item :label="$t('bookingAdmin.leaveReason')" prop="reason">
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="4"
            maxlength="200"
            show-word-limit
            :placeholder="$t('bookingAdmin.leaveReasonPlaceholder')" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="leaveDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="leaveSubmitting" @click="submitLeave">{{ $t('bookingAdmin.leaveSubmit') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="substituteDialogVisible"
      :title="$t('bookingAdmin.substituteTitle')"
      width="500px"
      destroy-on-close
      @closed="resetSubstituteForm">
      <div v-if="substituteBooking" class="mb-4 rounded-md bg-gray-50 p-4 text-sm">
        <div class="mb-1 font-500">{{ substituteBooking.booking_no }}</div>
        <div class="text-xs color-gray-500">
          {{ substituteBooking.booking_date }} {{ substituteBooking.start_time?.substring(0, 5) }}~{{ substituteBooking.end_time?.substring(0, 5) }}
        </div>
        <div class="mt-1 text-xs color-gray-500">
          {{ substituteBooking.student_name || '-' }} / {{ substituteBooking.teacher_name || '-' }} / {{ substituteBooking.course_name || '-' }}
        </div>
      </div>

      <el-form ref="substituteFormRef" :model="substituteForm" :rules="substituteRules" label-position="top">
        <el-form-item :label="$t('bookingAdmin.substituteTeacherLabel')" prop="substitute_teacher_id">
          <el-select
            v-model="substituteForm.substitute_teacher_id"
            filterable
            class="w-full"
            :placeholder="$t('bookingAdmin.substituteTeacherPlaceholder')"
            :loading="substituteTeachersLoading">
            <el-option
              v-for="teacher in substituteTeacherOptions"
              :key="teacher.id"
              :label="`${teacher.teacher_no || ''}${teacher.teacher_no ? ' - ' : ''}${teacher.name}${teacher.is_preferred ? ' ★' : ''}`"
              :value="teacher.id" />
          </el-select>
        </el-form-item>

        <div v-if="substituteForm.substitute_teacher_id && substituteContractsLoading" class="mb-4 text-sm color-gray-500">
          {{ $t('bookingAdmin.substituteContractLoading') }}
        </div>
        <div
          v-else-if="substituteForm.substitute_teacher_id && !substituteForm.substitute_contract_id"
          class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm color-red-600">
          {{ $t('bookingAdmin.substituteContractMissing') }}
        </div>

        <el-form-item :label="$t('bookingAdmin.substituteReason')" prop="reason">
          <el-input
            v-model="substituteForm.reason"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            :placeholder="$t('bookingAdmin.substituteReasonPlaceholder')" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="substituteDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="substituteSubmitting" @click="submitSubstitute">{{ $t('bookingAdmin.substituteSubmit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import dayjs from 'dayjs';
import {
  getBookingList, createBooking, updateBooking,
  batchCreateBookings, batchUpdateBookings, batchDeleteBookings,
  batchUpdateBookingsByIds, batchDeleteBookingsByIds,
  getBookingOptionSubstituteTeachers, getBookingOptionTeacherContracts,
  getBookingSlotAvailability,
  type BookingItem, type BookingListParams, type BookingStatus,
  type BookingSubstituteTeacherOption, type BookingSlotAvailability,
  type BookingSlotAvailabilityBlock, type BookingTeacherOption,
  type BookingCourseOption
} from '@/api/booking';
import { getZoomMeetingByBooking, createZoomMeeting, batchGetZoomMeetings, type ZoomMeetingLogResponse } from '@/api/zoom';
import { createLeaveRecord } from '@/api/leaveRecord';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { createSubstituteDetail, deleteSubstituteDetail } from '@/api/substituteDetail';
import { useBookingDependencies } from '@/composables/useBookingDependencies';
import { usePermissionStore } from '@/stores/permission';
import { copyToClipboardUtil } from '@/utils/clipboard';

const { t } = useI18n();
const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

// --- Filters & Table List ---
const filters = reactive({
  search: '', dateRange: [] as [string, string] | [], status: '' as BookingStatus | '',
  teacherId: '', studentId: '', courseId: ''
});

const { 
  studentOptions, 
  globalTeacherOptions: teacherOptions, 
  globalCourseOptions: courseOptions, 
  loadInitialOptions 
} = useBookingDependencies(filters);
const tableData = ref<BookingItem[]>([]);
const loading = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const selectedIds = ref<string[]>([]);
const bookingStatusOptions = computed(() => ([
  { value: 'pending', label: t('bookingShared.status.pending') },
  { value: 'confirmed', label: t('bookingShared.status.confirmed') },
  { value: 'completed', label: t('bookingShared.status.completed') },
  { value: 'cancelled', label: t('bookingShared.status.cancelled') },
]));
const weekdayOptionsLong = computed(() => ([
  { value: 0, label: t('teacherSchedule.mon') },
  { value: 1, label: t('teacherSchedule.tue') },
  { value: 2, label: t('teacherSchedule.wed') },
  { value: 3, label: t('teacherSchedule.thu') },
  { value: 4, label: t('teacherSchedule.fri') },
  { value: 5, label: t('teacherSchedule.sat') },
  { value: 6, label: t('teacherSchedule.sun') },
]));
const weekdayOptionsShort = computed(() => ([
  { value: 0, label: t('teacherSchedule.mon').replace(/^週/u, '') },
  { value: 1, label: t('teacherSchedule.tue').replace(/^週/u, '') },
  { value: 2, label: t('teacherSchedule.wed').replace(/^週/u, '') },
  { value: 3, label: t('teacherSchedule.thu').replace(/^週/u, '') },
  { value: 4, label: t('teacherSchedule.fri').replace(/^週/u, '') },
  { value: 5, label: t('teacherSchedule.sat').replace(/^週/u, '') },
  { value: 6, label: t('teacherSchedule.sun').replace(/^週/u, '') },
]));

const fetchData = async () => {
  loading.value = true;
  try {
    const params: BookingListParams = {
      page: currentPage.value, per_page: pageSize.value, search: filters.search || undefined,
      teacher_id: filters.teacherId || undefined, student_id: filters.studentId || undefined, course_id: filters.courseId || undefined,
      booking_status: filters.status || undefined,
    };
    if (filters.dateRange?.length === 2 && filters.dateRange[0]) {
      params.date_from = dayjs(filters.dateRange[0]).format('YYYY-MM-DD');
      params.date_to = dayjs(filters.dateRange[1]).format('YYYY-MM-DD');
    }
    const res = assertApiSuccess(await getBookingList(params), t('bookingAdmin.loadFailed'));
    tableData.value = res.data;
    total.value = res.total;
    fetchZoomInfos();
  } catch (e: any) {
    ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.loadFailed')));
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadInitialOptions();
  fetchData();
});

const handleFilterChange = () => { currentPage.value = 1; fetchData(); };
const handleReset = () => {
  filters.search = ''; filters.dateRange = []; filters.status = '';
  filters.teacherId = ''; filters.studentId = ''; filters.courseId = '';
  handleFilterChange();
};
const handlePaginationChange = () => { fetchData(); };
const handleSelectionChange = (val: BookingItem[]) => { selectedIds.value = val.map(v => v.id); };

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'success'; case 'cancelled': return 'info';
    case 'confirmed': return 'primary'; case 'pending': return 'warning';
    default: return '';
  }
};

// Zoom logic
const zoomInfoMap = ref<Record<string, ZoomMeetingLogResponse>>({});
const creatingZoomMap = ref<Record<string, boolean>>({});

const fetchZoomInfos = async () => {                                                                                                                                
  const activeBookings = tableData.value.filter(          
    b => ['pending', 'confirmed', 'completed'].includes(b.booking_status)                                                                                           
  );
  if (activeBookings.length === 0) return;                                                                                                                          
                                                                                                                                                                    
  const idsToFetch = activeBookings
    .filter(b => !zoomInfoMap.value[b.id])                                                                                                                          
    .map(b => b.id);                                      
  if (idsToFetch.length === 0) return;                                                                                                                              
 
  try {                                                                                                                                                             
    const res = assertApiSuccess(await batchGetZoomMeetings(idsToFetch), t('bookingAdmin.loadZoomFailed'));
    if (res.data) {
      Object.entries(res.data).forEach(([bookingId, meeting]) => {                                                                                                  
        zoomInfoMap.value[bookingId] = meeting;
      });                                                                                                                                                           
    }                                                     
  } catch (e) {
    // Fall back to per-booking fetch if the batch request fails.
    await Promise.allSettled(
      idsToFetch.map(async (id) => {                                                                                                                                
        try {                                             
          const res = assertApiSuccess(await getZoomMeetingByBooking(id), t('bookingAdmin.loadZoomFailed'));
          if (res.data) zoomInfoMap.value[id] = res.data; 
        } catch { /* ignore */ }                                                                                                                                    
      })
    );                                                                                                                                                              
  }                                                       
};

const handleCreateZoom = async (row: BookingItem) => {
  creatingZoomMap.value[row.id] = true;
  try {
    const res = assertApiSuccess(await createZoomMeeting({ booking_id: row.id }), t('bookingAdmin.createMeetingFailed'));
    if (res.data) zoomInfoMap.value[row.id] = res.data;
    ElMessage.success(res.message || t('bookingAdmin.createMeetingSuccess'));
  } catch(e:any) {
    ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.createMeetingFailed')));
  } finally {
    creatingZoomMap.value[row.id] = false;
  }
};

const copyToClipboard = (text: string | undefined | null) => {
  if (text) {
    copyToClipboardUtil(text, t('bookingAdmin.passcodeCopied'));
  }
};
const openUrl = (url?: string | null) => {
  if (url) window.open(url, '_blank');
};

const leaveDialogVisible = ref(false);
const leaveSubmitting = ref(false);
const leaveBooking = ref<BookingItem | null>(null);
const leaveFormRef = ref<FormInstance>();
const leaveForm = reactive({
  reason: '',
});
const leaveRules: FormRules = {
  reason: [{ required: true, message: t('bookingAdmin.leaveReasonRequired'), trigger: 'blur' }],
};

const substituteDialogVisible = ref(false);
const substituteSubmitting = ref(false);
const substituteTeachersLoading = ref(false);
const substituteContractsLoading = ref(false);
const substituteBooking = ref<BookingItem | null>(null);
const substituteFormRef = ref<FormInstance>();
const substituteTeacherOptions = ref<BookingSubstituteTeacherOption[]>([]);
const substituteForm = reactive({
  substitute_teacher_id: '',
  substitute_contract_id: '',
  reason: '',
});
const substituteRules: FormRules = {
  substitute_teacher_id: [{ required: true, message: t('bookingAdmin.substituteTeacherRequired'), trigger: 'change' }],
};

const openLeaveDialog = (row: BookingItem) => {
  if (row.booking_status !== 'confirmed') {
    ElMessage.warning(t('bookingAdmin.leaveOnlyConfirmed'));
    return;
  }
  if (row.has_pending_leave) {
    ElMessage.warning(t('bookingAdmin.leaveAlreadyPending'));
    return;
  }

  leaveBooking.value = row;
  leaveForm.reason = '';
  leaveDialogVisible.value = true;
};

const resetLeaveForm = () => {
  leaveBooking.value = null;
  leaveForm.reason = '';
  leaveFormRef.value?.clearValidate();
};

const submitLeave = async () => {
  if (!leaveFormRef.value || !leaveBooking.value) return;

  await leaveFormRef.value.validate(async (valid) => {
    if (!valid || !leaveBooking.value) return;

    try {
      await ElMessageBox.confirm(t('bookingAdmin.leaveConfirmMessage'), t('bookingAdmin.leaveConfirmTitle'), {
        confirmButtonText: t('bookingAdmin.leaveSubmit'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      });
    } catch {
      return;
    }

    leaveSubmitting.value = true;
    try {
      const res = assertApiSuccess(await createLeaveRecord({
        booking_id: leaveBooking.value.id,
        reason: leaveForm.reason.trim(),
      }), t('bookingAdmin.leaveFailed'));

      ElMessage.success(res.message || t('bookingAdmin.leaveSubmitted'));
      leaveDialogVisible.value = false;
      fetchData();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.leaveFailed')));
    } finally {
      leaveSubmitting.value = false;
    }
  });
};

const loadSubstituteTeacherOptions = async (bookingId: string) => {
  substituteTeachersLoading.value = true;
  try {
    const res = assertApiSuccess(await getBookingOptionSubstituteTeachers(bookingId), t('bookingAdmin.loadSubstituteTeachersFailed'));
    substituteTeacherOptions.value = res.data || [];
  } catch (error) {
    substituteTeacherOptions.value = [];
    ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.loadSubstituteTeachersFailed')));
  } finally {
    substituteTeachersLoading.value = false;
  }
};

const openSubstituteDialog = async (row: BookingItem) => {
  if (row.booking_status !== 'confirmed') {
    ElMessage.warning(t('bookingAdmin.substituteOnlyConfirmed'));
    return;
  }
  if (row.substitute_detail_id) {
    ElMessage.warning(t('bookingAdmin.substituteAlreadyAssigned'));
    return;
  }

  substituteBooking.value = row;
  substituteForm.substitute_teacher_id = '';
  substituteForm.substitute_contract_id = '';
  substituteForm.reason = '';
  substituteTeacherOptions.value = [];
  substituteDialogVisible.value = true;
  await loadSubstituteTeacherOptions(row.id);
};

const resetSubstituteForm = () => {
  substituteBooking.value = null;
  substituteTeacherOptions.value = [];
  substituteForm.substitute_teacher_id = '';
  substituteForm.substitute_contract_id = '';
  substituteForm.reason = '';
  substituteFormRef.value?.clearValidate();
};

watch(
  () => substituteForm.substitute_teacher_id,
  async (teacherId) => {
    substituteForm.substitute_contract_id = '';

    if (!teacherId) {
      substituteContractsLoading.value = false;
      return;
    }

    substituteContractsLoading.value = true;
    try {
      const res = assertApiSuccess(await getBookingOptionTeacherContracts(teacherId), t('bookingAdmin.loadTeacherContractsFailed'));
      const [firstContract] = res.data || [];
      if (firstContract) {
        substituteForm.substitute_contract_id = firstContract.id;
      } else {
        ElMessage.warning(t('bookingAdmin.substituteNoContract'));
      }
    } catch (error) {
      substituteForm.substitute_contract_id = '';
      ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.loadTeacherContractsFailed')));
    } finally {
      substituteContractsLoading.value = false;
    }
  }
);

const submitSubstitute = async () => {
  if (!substituteFormRef.value || !substituteBooking.value) return;

  await substituteFormRef.value.validate(async (valid) => {
    if (!valid || !substituteBooking.value) return;
    if (!substituteForm.substitute_contract_id) {
      ElMessage.warning(t('bookingAdmin.substituteNoContract'));
      return;
    }

    substituteSubmitting.value = true;
    try {
      const res = assertApiSuccess(await createSubstituteDetail({
        booking_id: substituteBooking.value.id,
        substitute_teacher_id: substituteForm.substitute_teacher_id,
        substitute_contract_id: substituteForm.substitute_contract_id,
        reason: substituteForm.reason.trim() || null,
      }), t('bookingAdmin.substituteFailed'));

      ElMessage.success(res.message || t('bookingAdmin.substituteSuccess'));
      substituteDialogVisible.value = false;
      fetchData();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.substituteFailed')));
    } finally {
      substituteSubmitting.value = false;
    }
  });
};

const handleCancelSubstitute = async (row: BookingItem) => {
  if (!row.substitute_detail_id) {
    ElMessage.warning(t('bookingAdmin.noSubstituteToCancel'));
    return;
  }

  try {
    await ElMessageBox.confirm(
      t('bookingAdmin.cancelSubstituteConfirmMessage', { bookingNo: row.booking_no }),
      t('bookingAdmin.cancelSubstituteTitle'),
      {
        confirmButtonText: t('bookingAdmin.confirmCancel'),
        cancelButtonText: t('bookingAdmin.goBack'),
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  try {
    const res = assertApiSuccess(await deleteSubstituteDetail(row.substitute_detail_id), t('bookingAdmin.cancelSubstituteFailed'));
    ElMessage.success(res.message || t('bookingAdmin.cancelSubstituteSuccess'));
    fetchData();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.cancelSubstituteFailed')));
  }
};

const handleCancelBooking = async (row: BookingItem) => {
  try {
    await ElMessageBox.confirm(t('bookingAdmin.cancelBookingConfirmMessage', { bookingNo: row.booking_no }), t('bookingAdmin.cancelBookingTitle'), {
      confirmButtonText: t('bookingAdmin.nextStep'),
      cancelButtonText: t('bookingAdmin.goBack'),
      type: 'warning',
    });
  } catch {
    return;
  }

  try {
    await ElMessageBox.confirm(t('bookingAdmin.secondConfirmMessage'), t('bookingAdmin.secondConfirmTitle'), {
      confirmButtonText: t('bookingAdmin.confirmCancel'),
      cancelButtonText: t('bookingAdmin.keepBooking'),
      type: 'error',
    });
  } catch {
    return;
  }

  try {
    const res = assertApiSuccess(await updateBooking(row.id, {
      booking_status: 'cancelled',
    }), t('bookingAdmin.cancelBookingFailed'));

    ElMessage.success(res.message || t('bookingAdmin.cancelBookingSuccess'));
    fetchData();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.cancelBookingFailed')));
  }
};

// --- Dialog state management ---
const dialogs = reactive({
  add: { visible: false, loading: false },
  edit: { visible: false, loading: false, editId: '' },
  batchCreate: { visible: false, loading: false },
  batchUpdate: { visible: false, loading: false },
  batchDelete: { visible: false, loading: false },
  batchUpdateByIds: { visible: false, loading: false },
});

const openDialog = (name: keyof typeof dialogs, row?: BookingItem) => {
  dialogs[name].visible = true;
  if (name === 'edit' && row) {
    dialogs.edit.editId = row.id;
    Object.assign(editForm, { 
      student_name: row.student_name, 
      teacher_name: row.teacher_name, 
      course_name: row.course_name, 
      booking_status: row.booking_status,
      booking_date: row.booking_date,
      start_time: row.start_time?.substring(0,5) || '',
      end_time: row.end_time?.substring(0,5) || '', 
      notes: row.notes || '' 
    });
  }
};

const resetForm = (name: string) => {
  if(name === 'add') { addFormRef.value?.resetFields(); addDeps.resetOptions(); resetSlotAvailability(); }
  if(name === 'edit') { editFormRef.value?.resetFields(); dialogs.edit.editId=''; }
  if(name === 'batchCreate') { batchCreateRef.value?.resetFields(); batchCreateForm.weekdays=[]; batchCreateForm.daterange=[]; batchCreateDeps.resetOptions(); }
  if(name === 'batchUpdate') { batchUpdateRef.value?.resetFields(); batchUpdateForm.weekdays=[]; batchUpdateForm.daterange=[]; batchUpdateDeps.resetOptions(); }
  if(name === 'batchDelete') { batchDeleteRef.value?.resetFields(); batchDeleteForm.weekdays=[]; batchDeleteForm.daterange=[]; batchDeleteDeps.resetOptions(); }
  if(name === 'batchUpdateByIds') { batchUpdateByIdsRef.value?.resetFields(); batchUpdateByIdsForm.notes=''; }
};

// Add Dialog Section
const addFormRef = ref<FormInstance>();
const addForm = reactive({
  student_id: '', student_contract_id: '', teacher_id: '', course_id: '',
  timeMode: 'manual', booking_date: '', start_time: '', end_time: '', teacher_slot_id: '', slot_block_time: '', notes: ''
});
const addDeps = reactive(useBookingDependencies(addForm, addFormRef));
const slotAvailability = ref<BookingSlotAvailability | null>(null);
const slotAvailabilityLoading = ref(false);
const selectedSlotStartBlock = ref<BookingSlotAvailabilityBlock | null>(null);
const selectedSlotEndBlock = ref<BookingSlotAvailabilityBlock | null>(null);
let slotAvailabilityRequestId = 0;

const formatTeacherOptionLabel = (teacher: BookingTeacherOption) => {
  return teacher.teacher_no ? `${teacher.teacher_no} - ${teacher.name}` : teacher.name;
};

const formatCourseOptionLabel = (course: BookingCourseOption) => {
  return course.course_code ? `${course.course_code} - ${course.course_name}` : course.course_name;
};

const validateBookingDate = (_rule: any, value: any, callback: any) => {
  if (addForm.timeMode === 'manual' && !value) callback(new Error(t('bookingAdmin.required')));
  else callback();
};

const validateSlotBlockTime = (_rule: any, value: any, callback: any) => {
  if (addForm.timeMode === 'slot' && addForm.teacher_slot_id && !value) {
    callback(new Error(t('bookingAdmin.selectAvailableTimeBlock')));
    return;
  }
  callback();
};

const addRules: FormRules = {
  student_id: [{ required: true, message: t('bookingAdmin.required'), trigger: 'change' }],
  teacher_id: [{ required: true, message: t('bookingAdmin.required'), trigger: 'change' }],
  course_id: [{ required: true, message: t('bookingAdmin.required'), trigger: 'change' }],
  booking_date: [{ validator: validateBookingDate, trigger: 'change' }],
  slot_block_time: [{ validator: validateSlotBlockTime, trigger: 'change' }]
};

const resetSlotAvailability = () => {
  slotAvailabilityRequestId += 1;
  slotAvailability.value = null;
  slotAvailabilityLoading.value = false;
  selectedSlotStartBlock.value = null;
  selectedSlotEndBlock.value = null;
  addForm.slot_block_time = '';
  if (addForm.timeMode === 'slot') {
    addForm.booking_date = '';
    addForm.start_time = '';
    addForm.end_time = '';
  }
};

const formatApiTime = (time?: string | null) => time?.substring(0, 5) || '';
const formatSlotBlockTime = (block: BookingSlotAvailabilityBlock) => {
  return `${formatApiTime(block.start_time)}~${formatApiTime(block.end_time)}`;
};

const getSlotBlockIndex = (block: BookingSlotAvailabilityBlock) => {
  return slotAvailability.value?.blocks.findIndex((item) => (
    item.start_time === block.start_time && item.end_time === block.end_time
  )) ?? -1;
};

const isSelectedSlotBlock = (block: BookingSlotAvailabilityBlock) => {
  if (!selectedSlotStartBlock.value) return false;
  const blockIndex = getSlotBlockIndex(block);
  const startIndex = getSlotBlockIndex(selectedSlotStartBlock.value);
  const endIndex = selectedSlotEndBlock.value ? getSlotBlockIndex(selectedSlotEndBlock.value) : startIndex;
  return blockIndex >= startIndex && blockIndex <= endIndex;
};

const isSameSlotBlock = (a: BookingSlotAvailabilityBlock | null, b: BookingSlotAvailabilityBlock) => (
  a?.start_time === b.start_time && a?.end_time === b.end_time
);

const isSlotStartAndEndBlock = (block: BookingSlotAvailabilityBlock) => (
  isSameSlotBlock(selectedSlotStartBlock.value, block) && isSameSlotBlock(selectedSlotEndBlock.value, block)
);

const getSlotBlockSelectionText = (block: BookingSlotAvailabilityBlock) => {
  if (isSlotStartAndEndBlock(block)) return t('bookingAdmin.slotStartAndEndSelected');
  const isStart = isSameSlotBlock(selectedSlotStartBlock.value, block);
  const isEnd = isSameSlotBlock(selectedSlotEndBlock.value, block);
  if (isStart) return t('bookingAdmin.slotStartSelected');
  if (isEnd) return t('bookingAdmin.slotEndSelected');
  return '';
};

const selectSlotBlock = (block: BookingSlotAvailabilityBlock) => {
  if (!block.is_available || !slotAvailability.value) return;
  const blocks = slotAvailability.value.blocks;

  if (!selectedSlotStartBlock.value || selectedSlotEndBlock.value) {
    selectedSlotStartBlock.value = block;
    selectedSlotEndBlock.value = null;
    addForm.booking_date = slotAvailability.value.slot_date;
    addForm.start_time = formatApiTime(block.start_time);
    addForm.end_time = '';
    addForm.slot_block_time = '';
    return;
  }

  const startIndex = getSlotBlockIndex(selectedSlotStartBlock.value);
  const endIndex = getSlotBlockIndex(block);

  if (endIndex < startIndex) {
    selectedSlotStartBlock.value = block;
    selectedSlotEndBlock.value = null;
    addForm.booking_date = slotAvailability.value.slot_date;
    addForm.start_time = formatApiTime(block.start_time);
    addForm.end_time = '';
    addForm.slot_block_time = '';
    return;
  }

  const selectedRange = blocks.slice(startIndex, endIndex + 1);
  if (selectedRange.some((item) => !item.is_available)) {
    ElMessage.warning(t('bookingAdmin.selectContinuousAvailableBlocks'));
    return;
  }

  selectedSlotEndBlock.value = block;
  addForm.booking_date = slotAvailability.value.slot_date;
  addForm.start_time = formatApiTime(selectedSlotStartBlock.value.start_time);
  addForm.end_time = formatApiTime(block.end_time);
  addForm.slot_block_time = `${addForm.start_time}-${addForm.end_time}`;
  addFormRef.value?.clearValidate(['slot_block_time']);
};

const handleTeacherSlotChange = async (slotId: string) => {
  resetSlotAvailability();
  if (!slotId) return;

  const requestId = ++slotAvailabilityRequestId;
  slotAvailabilityLoading.value = true;
  try {
    const res = assertApiSuccess(await getBookingSlotAvailability(slotId), t('bookingAdmin.loadSlotAvailabilityFailed'));
    if (requestId !== slotAvailabilityRequestId) return;
    slotAvailability.value = res.data;
  } catch (error) {
    if (requestId === slotAvailabilityRequestId) {
      ElMessage.error(getApiErrorMessage(error, t('bookingAdmin.loadSlotAvailabilityFailed')));
    }
  } finally {
    if (requestId === slotAvailabilityRequestId) {
      slotAvailabilityLoading.value = false;
    }
  }
};

const handleAddStudentChange = async () => {
  resetSlotAvailability();
  await addDeps.handleStudentChange();
};

const handleAddTeacherChange = async () => {
  resetSlotAvailability();
  await addDeps.handleTeacherChange(true);
};

const handleAddTimeModeChange = () => {
  resetSlotAvailability();
  if (addForm.timeMode === 'manual') {
    addForm.teacher_slot_id = '';
  } else {
    addForm.booking_date = '';
    addForm.start_time = '';
    addForm.end_time = '';
  }
};

const submitAdd = async () => {
  if (!addFormRef.value) return;
  await addFormRef.value.validate(async (valid) => {
    if (!valid) return;
    dialogs.add.loading = true;
    try {
      const data: any = {
        student_id: addForm.student_id, teacher_id: addForm.teacher_id,
        course_id: addForm.course_id, notes: addForm.notes || null,
        booking_date: addForm.booking_date || dayjs().format('YYYY-MM-DD')
      };
      if(addForm.student_contract_id) data.student_contract_id = addForm.student_contract_id;
      if(addForm.timeMode === 'manual') {
        if(!addForm.start_time || !addForm.end_time) {
          ElMessage.warning(t('bookingAdmin.completeTimeRequired'));
          dialogs.add.loading = false;
          return;
        }
        data.start_time = addForm.start_time.substring(0,5); data.end_time = addForm.end_time.substring(0,5);
      } else {
        if(!addForm.teacher_slot_id) {
          ElMessage.warning(t('bookingAdmin.selectTeacherSlot'));
          dialogs.add.loading = false;
          return;
        }
        if(!selectedSlotStartBlock.value || !selectedSlotEndBlock.value || !slotAvailability.value) {
          ElMessage.warning(t('bookingAdmin.selectAvailableTimeBlock'));
          dialogs.add.loading = false;
          return;
        }
        data.teacher_slot_id = addForm.teacher_slot_id;
        data.booking_date = slotAvailability.value.slot_date;
        data.start_time = formatApiTime(selectedSlotStartBlock.value.start_time);
        data.end_time = formatApiTime(selectedSlotEndBlock.value.end_time);
      }
      const res = assertApiSuccess(await createBooking(data), t('bookingAdmin.addFailed'));
      ElMessage.success(res.message || t('bookingAdmin.addSuccess'));
      dialogs.add.visible = false;
      fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.addFailed'))); }
    finally { dialogs.add.loading = false; }
  });
};

// Edit Single Dialog
const editFormRef = ref<FormInstance>();
const editForm = reactive({ 
  id: '',
  booking_status: 'pending' as BookingStatus, 
  end_time: '', 
  notes: '', 
  student_name: '', 
  teacher_name: '', 
  course_name: '', 
  booking_date: '', 
  start_time: '' 
});
const editRules: FormRules = { booking_status: [{ required: true, message: t('bookingAdmin.required') }] };
const submitEdit = async () => {
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid) => {
    if(!valid) return;
    dialogs.edit.loading = true;
    try {
      const res = assertApiSuccess(await updateBooking(dialogs.edit.editId, {
        booking_status: editForm.booking_status,
        end_time: editForm.end_time.substring(0,5) || null,
        notes: editForm.notes || null
      }), t('bookingAdmin.updateFailed'));
      ElMessage.success(res.message || t('bookingAdmin.updateSuccess'));
      dialogs.edit.visible = false;
      fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.updateFailed'))); }
    finally { dialogs.edit.loading = false; }
  });
};

// Batch Update By IDs Dialog
const batchUpdateByIdsRef = ref<FormInstance>();
const batchUpdateByIdsForm = reactive({ booking_status: 'confirmed' as BookingStatus, notes: '' });
const submitBatchUpdateByIds = async () => {
  dialogs.batchUpdateByIds.loading = true;
  try {
    const res = assertApiSuccess(await batchUpdateBookingsByIds({ booking_ids: selectedIds.value, booking_status: batchUpdateByIdsForm.booking_status, notes: batchUpdateByIdsForm.notes || null }), t('bookingAdmin.operationFailed'));
    ElMessage.success(res.message || t('bookingAdmin.batchUpdateSuccess'));
    dialogs.batchUpdateByIds.visible = false;
    selectedIds.value = [];
    fetchData();
  } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.operationFailed'))); }
  finally { dialogs.batchUpdateByIds.loading = false; }
};

// Batch Delete By IDs
const handleDelete = (row: BookingItem) => {
  ElMessageBox.confirm(t('bookingAdmin.deleteConfirmMessage'), t('bookingAdmin.deleteTitle'), { type: 'error' }).then(async () => {
    try {
      const res = assertApiSuccess(await batchDeleteBookingsByIds({ booking_ids: [row.id] }), t('bookingAdmin.deleteFailed'));
      ElMessage.success(res.message || t('bookingAdmin.deleted'));
      fetchData();
    }
    catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.deleteFailed'))); }
  });
};
const handleBatchDeleteByIds = () => {
  ElMessageBox.confirm(t('bookingAdmin.batchDeleteConfirmMessage', { count: selectedIds.value.length }), t('bookingAdmin.batchDelete'), { type: 'error' }).then(async () => {
    try {
      const res = assertApiSuccess(await batchDeleteBookingsByIds({ booking_ids: selectedIds.value }), t('bookingAdmin.deleteFailed'));
      ElMessage.success(res.message || t('bookingAdmin.deleted'));
      selectedIds.value = [];
      fetchData();
    }
    catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.deleteFailed'))); }
  });
};

// Periodic Batch Create Dialog
const batchCreateRef = ref<FormInstance>();
const batchCreateForm = reactive({ student_id:'', student_contract_id: '', teacher_id:'', course_id:'', daterange: [] as any[], weekdays: [] as number[], start_time:'', end_time:'', notes:'' });
const batchCreateDeps = reactive(useBookingDependencies(batchCreateForm, batchCreateRef));
const batchCreateRules: FormRules = {
    student_id: [{ required: true, message: t('bookingAdmin.required') }], teacher_id: [{ required: true, message: t('bookingAdmin.required') }], course_id: [{ required: true, message: t('bookingAdmin.required') }]
};
const submitBatchCreate = async () => {
  if(!batchCreateRef.value) return;
  await batchCreateRef.value.validate(async v => {
    if(!v || !batchCreateForm.daterange || batchCreateForm.daterange.length !== 2) { if(!v) return; ElMessage.warning(t('bookingAdmin.dateRangeRequired')); return; }
    dialogs.batchCreate.loading = true;
    try {
      const res = assertApiSuccess(await batchCreateBookings({
        student_id: batchCreateForm.student_id, teacher_id: batchCreateForm.teacher_id, course_id: batchCreateForm.course_id,
        student_contract_id: batchCreateForm.student_contract_id || null,
        start_date: batchCreateForm.daterange[0], end_date: batchCreateForm.daterange[1],
        weekdays: batchCreateForm.weekdays.length > 0 ? batchCreateForm.weekdays : null,
        start_time: batchCreateForm.start_time.substring(0,5) || null, end_time: batchCreateForm.end_time.substring(0,5) || null, notes: batchCreateForm.notes || null,
      }), t('bookingAdmin.createFailed'));
      ElMessage.success(res.message || t('bookingAdmin.batchCreateSuccess')); dialogs.batchCreate.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.createFailed'))); }
    finally { dialogs.batchCreate.loading = false; }
  });
};

// Periodic Batch Update Dialog
const batchUpdateRef = ref<FormInstance>();
const batchUpdateForm = reactive({ daterange: [] as any[], weekdays: [] as number[], student_id:'', teacher_id:'', course_id:'', filter_status:'' as any, new_status:'confirmed' as any, notes:'' });
const batchUpdateDeps = reactive(useBookingDependencies(batchUpdateForm, batchUpdateRef));
const batchUpdateRules: FormRules = { new_status: [{ required: true, message: t('bookingAdmin.required') }] };
const submitBatchUpdate = async () => {
  if(!batchUpdateRef.value) return;
  await batchUpdateRef.value.validate(async v => {
    if(!v || !batchUpdateForm.daterange || batchUpdateForm.daterange.length !== 2) { if(!v) return; ElMessage.warning(t('bookingAdmin.dateRangeRequired')); return; }
    dialogs.batchUpdate.loading = true;
    try {
      const res = assertApiSuccess(await batchUpdateBookings({
        start_date: batchUpdateForm.daterange[0], end_date: batchUpdateForm.daterange[1],
        weekdays: batchUpdateForm.weekdays.length > 0 ? batchUpdateForm.weekdays : null,
        student_id: batchUpdateForm.student_id || null, teacher_id: batchUpdateForm.teacher_id || null, course_id: batchUpdateForm.course_id || null,
        filter_status: batchUpdateForm.filter_status || null, new_status: batchUpdateForm.new_status, notes: batchUpdateForm.notes || null
      }), t('bookingAdmin.updateFailed'));
      ElMessage.success(res.message || t('bookingAdmin.batchUpdateSuccess')); dialogs.batchUpdate.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.updateFailed'))); }
    finally { dialogs.batchUpdate.loading = false; }
  });
};

// Periodic Batch Delete Dialog
const batchDeleteRef = ref<FormInstance>();
const batchDeleteForm = reactive({ daterange: [] as any[], weekdays: [] as number[], student_id:'', teacher_id:'', course_id:'', filter_status:'' as any });
const batchDeleteDeps = reactive(useBookingDependencies(batchDeleteForm, batchDeleteRef));
const batchDeleteRules: FormRules = { };
const submitBatchDelete = async () => {
  if(!batchDeleteRef.value) return;
  await batchDeleteRef.value.validate(async v => {
    if(!v || !batchDeleteForm.daterange || batchDeleteForm.daterange.length !== 2) { if(!v) return; ElMessage.warning(t('bookingAdmin.dateRangeRequired')); return; }
    dialogs.batchDelete.loading = true;
    try {
      const res = assertApiSuccess(await batchDeleteBookings({
        start_date: batchDeleteForm.daterange[0], end_date: batchDeleteForm.daterange[1],
        weekdays: batchDeleteForm.weekdays.length > 0 ? batchDeleteForm.weekdays : null,
        student_id: batchDeleteForm.student_id || null, teacher_id: batchDeleteForm.teacher_id || null, course_id: batchDeleteForm.course_id || null,
        filter_status: batchDeleteForm.filter_status || null
      }), t('bookingAdmin.deleteFailed'));
      ElMessage.success(res.message || t('bookingAdmin.batchDeleteSuccess')); dialogs.batchDelete.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, t('bookingAdmin.deleteFailed'))); }
    finally { dialogs.batchDelete.loading = false; }
  });
};
</script>

<style scoped>
:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}

.slot-block-start-end {
  color: #00ffff;
}
</style>
