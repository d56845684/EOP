<template>
  <div class="booking-list pl-2 pr-4">
    <!-- Quick Batch Actions Top -->
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="text-lg my-0">{{ $t('menu.booking_mgmt') }}</h3>
      <div class="flex gap-1">
        <el-button 
          v-permission="'bookings.batch_create'" 
          type="success" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchCreate')">
            <template #icon><div class="i-hugeicons:add-circle" /></template>
            批次建立預約
        </el-button>
        <el-button 
          v-permission="'bookings.batch_update'" 
          type="warning" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchUpdate')">
            <template #icon><div class="i-hugeicons:edit-02" /></template>
            批次更新預約
        </el-button>
        <el-button 
          v-permission="'bookings.batch_delete'" 
          type="danger" 
          size="small" 
          round 
          plain 
          class="h-30px! px-2!" 
          @click="openDialog('batchDelete')">
            <template #icon><div class="i-hugeicons:delete-02" /></template>
            批次刪除預約
        </el-button>
        <el-button
          v-permission="'bookings.create'"
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
        <el-form-item label="關鍵字">
          <el-input 
            v-model="filters.search" 
            placeholder="搜尋編號、姓名" 
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
            <el-option v-for="(label, value) in BOOKING_STATUS_MAP" :key="value" :label="label" :value="value" />
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
            <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
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
            <el-option v-for="s in studentOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="課程">
          <el-select v-model="filters.courseId" placeholder="全部" clearable filterable class="w-160px!" @change="handleFilterChange">
            <el-option v-for="c in courseOptions" :key="c.id" :label="c.course_name" :value="c.id" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round size="small" class="h-30px!" @click="handleFilterChange">
            <template #icon><div class="i-hugeicons:search-01" /></template>搜尋
          </el-button>
          <el-button round size="small" class="h-30px!" @click="handleReset">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table Toolbar -->
    <div class="mb-2">
      <el-button 
        type="warning"
        round
        size="small"
        plain 
        class="h-30px!"
        :disabled="selectedIds.length === 0" 
        @click="openDialog('batchUpdateByIds')">
        <template #icon><div class="i-hugeicons:edit-02" /></template>
        批次更新狀態
      </el-button>
      <el-button 
        type="danger" 
        plain 
        round
        size="small"
        class="h-30px!"
        :disabled="selectedIds.length === 0" 
        @click="handleBatchDeleteByIds">
        <template #icon><div class="i-hugeicons:delete-02" /></template>
        批次刪除
      </el-button>
    </div>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="tableData" style="width: 100%" v-loading="loading" stripe size="small" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="40" align="center" fixed="left" />
        <el-table-column label="預約編號" prop="booking_no" width="200">
          <template #default="{ row }">
            <div class="flex justify-between items-center gap-2 pr-3">
              <div class="font-bold">{{ row.booking_no }}</div>
              <el-tag 
                :type="row.booking_type === 'trial' ? 'warning' : ''" 
                effect="plain" 
                size="small"
                class="h-20px! text-10px! px-1!">
                {{ BOOKING_TYPE_MAP[row.booking_type] || row.booking_type }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.student')" min-width="100">
          <template #default="{ row }">{{ row.student_name || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('common.teacher')" min-width="100">
          <template #default="{ row }">
            <div>{{ row.teacher_name || '-' }}</div>
            <div v-if="row.substitute_teacher_name" class="text-xs color-gray-500 mt-1">
              {{ row.substitute_teacher_name }}（代課）
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.course')" min-width="120">
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
        <el-table-column :label="$t('common.status')" width="80" align="center">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusColor(row.booking_status)" 
              size="small"
              class="text-11px! bg-transparent!">
              <div class="flex items-center gap-1">
                <span :class="`text-sm color-${getStatusColor(row.booking_status)}`">•</span>
                <span>{{ BOOKING_STATUS_MAP[row.booking_status] }}</span>
              </div>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="ZOOM" width="150" align="center">
          <template #default="{ row }">
            <template v-if="['pending', 'confirmed', 'completed'].includes(row.booking_status)">
              <div v-if="!zoomInfoMap[row.id]" class="flex justify-center items-center min-h-12">
                <el-button 
                  type="primary" 
                  size="small" 
                  plain
                  round
                  class="text-xs h-20px! px-1.5!"
                  :loading="creatingZoomMap[row.id]"
                  @click="handleCreateZoom(row)">
                  <template #icon><div class="i-hugeicons:meeting-room" /></template>
                  建立會議
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
                    <template #icon><div class="i-hugeicons:video-01" /></template>加入會議
                  </el-button>
                  <div 
                    v-if="zoomInfoMap[row.id]?.passcode" 
                    class="flex items-center gap-0.5 text-11px leading-12px color-gray-400 translate-x-10px">
                    密碼: {{ zoomInfoMap[row.id]?.passcode }}
                    <el-button size="small" round link class="text-xs h-20px! px-1! color-gray-400! hover:color-gray-500!" @click="copyToClipboard(zoomInfoMap[row.id]?.passcode)"><div class="i-hugeicons:copy-01" /></el-button>
                </div>
                </div>
                <el-button 
                  v-if="zoomInfoMap[row.id]?.recording_url || zoomInfoMap[row.id]?.drive_view_link"
                  type="info" 
                  size="small" 
                  round
                  plain
                  class="text-xs h-20px! px-1.5!"
                  @click="openUrl(zoomInfoMap[row.id]?.recording_url || zoomInfoMap[row.id]?.drive_view_link)">
                  <template #icon><div class="i-hugeicons:video-replay" /></template>取得錄影
                </el-button>
              </div>
            </template>
            <div v-else class="flex justify-center items-center min-h-12">
              <span class="text-gray-400">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div class="flex flex-col justify-between gap-2 items-start px-1">
              <div>
                <el-button link type="primary" size="small" @click="openDialog('edit', row)">{{ $t('common.edit') }}</el-button>
                <el-button link type="danger" size="small" @click="handleDelete(row)">
                  <template #icon><div class="i-hugeicons:delete-02" /></template>
                  {{ $t('common.delete') }}
                </el-button>
              </div>
              <template v-if="row.booking_status === 'confirmed'">
                <div class="flex justify-center gap-2 mt-2">
                  <div>
                    <el-button
                      plain
                      type="warning"
                      size="small"
                      round
                      :disabled="Boolean(row.has_pending_leave)"
                      @click="openLeaveDialog(row)">
                      請假
                    </el-button>
                  </div>
                  <div>
                    <el-button
                    v-if="!row.substitute_detail_id"
                    plain
                    type="success"
                    size="small"
                    round
                    @click="openSubstituteDialog(row)">
                    代課
                  </el-button>
                  <el-button
                    v-else
                    plain
                    type="danger"
                    size="small"
                    round
                    @click="handleCancelSubstitute(row)">
                    取消代課
                  </el-button>
                  </div>
                  <div>
                    <el-button plain type="danger" size="small" round @click="handleCancelBooking(row)">
                      取消
                    </el-button>
                  </div>
              </div>
            </template>
            </div>
                <!-- <div class="flex flex-wrap justify-center gap-x-2 gap-y-1">
              <template v-if="row.booking_status === 'confirmed'">
                <el-button
                  plain
                  type="warning"
                  size="small"
                  round
                  :disabled="Boolean(row.has_pending_leave)"
                  @click="openLeaveDialog(row)">
                  請假
                </el-button>
                <el-button
                  v-if="!row.substitute_detail_id"
                  plain
                  type="success"
                  size="small"
                  round
                  @click="openSubstituteDialog(row)">
                  代課
                </el-button>
                <el-button
                  v-else
                  plain
                  type="danger"
                  size="small"
                  round
                  @click="handleCancelSubstitute(row)">
                  取消代課
                </el-button>
                <el-button plain type="danger" round size="small" @click="handleCancelBooking(row)">
                  取消
                </el-button>
              </template>
              <el-button link type="primary" size="small" @click="openDialog('edit', row)">{{ $t('common.edit') }}</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">
                <template #icon><div class="i-hugeicons:delete-02" /></template>
                {{ $t('common.delete') }}
              </el-button>
            </div> -->
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
    <el-drawer v-model="dialogs.add.visible" title="新增預約" size="480px" @closed="resetForm('add')">
        <el-form :model="addForm" :rules="addRules" ref="addFormRef" size="small" label-width="80px" label-position="top">
          <el-row>
            <el-col :span="10">

              <el-form-item label="學生" prop="student_id">
                  <el-select v-model="addForm.student_id" filterable placeholder="請先選擇學生" class="w-full" @change="addDeps.handleStudentChange()">
                      <el-option v-for="s in studentOptions" :key="s.id" :label="s.name" :value="s.id" />
                  </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="10" :push="2">
              <el-form-item label="合約(可選)" prop="student_contract_id">
                  <el-select 
                    v-model="addForm.student_contract_id" 
                    filterable 
                    clearable 
                    placeholder="選擇合約" 
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
              <el-form-item label="教師" prop="teacher_id">
                <el-select 
                  v-model="addForm.teacher_id" 
                  filterable 
                  placeholder="選擇教師" 
                  class="w-full" 
                  :disabled="!addForm.student_id" 
                  @change="addDeps.handleTeacherChange(true)" 
                  :loading="addDeps.isFetchingTeachers">
                    <el-option v-for="t in addDeps.teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="10" :push="2">
              <el-form-item label="課程" prop="course_id">
                <el-select 
                  v-model="addForm.course_id" 
                  filterable 
                  placeholder="選擇課程" 
                  class="w-full" 
                  :disabled="!addForm.student_id || !addForm.teacher_id" 
                  :loading="addDeps.isFetchingCourses">
                    <el-option v-for="c in addDeps.courseOptions" :key="c.id" :label="c.course_name" :value="c.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="16">
              <el-form-item label="時間模式">
                  <el-radio-group v-model="addForm.timeMode" :disabled="!addForm.teacher_id">
                      <el-radio label="manual">自訂時間</el-radio>
                      <el-radio label="slot">選擇教師時段</el-radio>
                  </el-radio-group>
            </el-form-item>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="16">
            <!-- Manual Mode -->
            <template v-if="addForm.timeMode === 'manual'">
                <el-form-item label="日期" prop="booking_date">
                    <el-date-picker 
                      v-model="addForm.booking_date" 
                      type="date" 
                      value-format="YYYY-MM-DD" 
                      placeholder="選擇日期" 
                      class="w-full h-30px!" 
                      :disabled="!addForm.teacher_id" />
                </el-form-item>
                <el-form-item label="時間" required>
                    <div class="flex gap-2 w-full">
                        <el-time-picker 
                          v-model="addForm.start_time" 
                          format="HH:mm" 
                          value-format="HH:mm" 
                          placeholder="開始" 
                          class="flex-1 h-30px!" />
                        <span class="mt-1">-</span>
                        <el-time-picker 
                          v-model="addForm.end_time" 
                          format="HH:mm" 
                          value-format="HH:mm" 
                          placeholder="結束" 
                          class="flex-1 h-30px!" />
                    </div>
                </el-form-item>
            </template>
            </el-col>
            <el-col :span="12">
              <!-- Slot Mode -->
              <template v-if="addForm.timeMode === 'slot'">
                <el-form-item label="教師時段" prop="teacher_slot_id">
                  <el-select 
                    v-model="addForm.teacher_slot_id" 
                    placeholder="請選擇時段" 
                    class="w-full" 
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
                      :disabled="slot.is_booked" 
                    >
                      <div class="flex gap-2">
                        <span class="font-500 w-85px">{{ dayjs(slot.slot_date).format('YYYY/MM/DD') }}</span>
                        <span class="font-500">{{ slot.start_time.substring(0,5)}}~{{ slot.end_time.substring(0,5)}}</span>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </template>
            </el-col>
          </el-row>
          <el-row>
            <el-col :span="23">
              <el-form-item label="備註" prop="notes">
                  <el-input v-model="addForm.notes" type="textarea" :rows="4" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <template #footer>
            <el-button size="small" round class="h-30px! px-4!" @click="dialogs.add.visible = false">{{ $t('common.cancel') }}</el-button>
            <el-button size="small" type="primary" round class="h-30px! px-4!" @click="submitAdd" :loading="dialogs.add.loading">新增</el-button>
        </template>
    </el-drawer>

    <!-- Single Edit Booking -->
    <el-drawer v-model="dialogs.edit.visible" title="編輯預約" size="480px" @closed="resetForm('edit')">
      <div class="mb-8 p-4 bg-gray-100 rounded-md">
        <div class="font-500 mb-4 text-xs color-[#3f4254]">預約資訊</div>
        <div class="flex flex-col gap-2 text-xs">
          <div><label class="color-[#7e8299] mr-2">學生</label><span class="color-[#3f4254]">{{ editForm?.student_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">教師</label><span class="color-[#3f4254]">{{ editForm?.teacher_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">課程</label><span class="color-[#3f4254]">{{ editForm?.course_name || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">日期</label><span class="color-[#3f4254]">{{ editForm?.booking_date || '-' }}</span></div>
          <div><label class="color-[#7e8299] mr-2">時間</label><span class="color-[#3f4254]">{{ editForm?.start_time || '-' }} - {{ editForm?.end_time || '-' }}</span></div>
        </div>
      </div>
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" size="small" label-width="72px" label-position="top">
          <el-form-item label="狀態" prop="booking_status">
            <el-select v-model="editForm.booking_status" class="w-150px">
              <el-option label="待確認" value="pending" />
              <el-option label="已確認" value="confirmed" />
              <el-option label="已完成" value="completed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </el-form-item>
          <el-form-item label="結束時間" prop="end_time">
            <el-time-picker 
              v-model="editForm.end_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              placeholder="縮短結束時間" 
              class="w-150px! h-30px!" />
            <div class="text-xs text-gray-400 ml-4">僅可縮短時間，無法延長。</div>
          </el-form-item>
          <el-form-item label="備註" prop="notes">
            <el-input v-model="editForm.notes" type="textarea" :rows="4" />
          </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" round class="h-30px! px-4!" @click="dialogs.edit.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" round class="h-30px! px-4!" @click="submitEdit" :loading="dialogs.edit.loading">更新</el-button>
      </template>
    </el-drawer>

    <!-- Batch Update By Ids -->
    <el-dialog 
      v-model="dialogs.batchUpdateByIds.visible" 
      title="批次更新狀態" 
      width="400px" 
      @closed="resetForm('batchUpdateByIds')">
      <el-form 
        :model="batchUpdateByIdsForm" 
        ref="batchUpdateByIdsRef" 
        label-width="80px">
          <el-form-item label="新狀態">
            <el-select v-model="batchUpdateByIdsForm.booking_status" class="w-full">
              <el-option v-for="(label, value) in BOOKING_STATUS_MAP" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="備註">
            <el-input v-model="batchUpdateByIdsForm.notes" type="textarea" />
          </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.batchUpdateByIds.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button 
          type="primary" 
          @click="submitBatchUpdateByIds" 
          :loading="dialogs.batchUpdateByIds.loading">更新</el-button>
      </template>
    </el-dialog>

    <!-- Periodic Batch Create -->
    <el-dialog 
      v-model="dialogs.batchCreate.visible" 
      title="批次建立預約" 
      width="600px" 
      @closed="resetForm('batchCreate')">
      <el-form :model="batchCreateForm" :rules="batchCreateRules" ref="batchCreateRef" label-width="120px">
        <el-form-item label="學生" prop="student_id">
            <el-select v-model="batchCreateForm.student_id" filterable placeholder="請先選擇學生" class="w-full" @change="batchCreateDeps.handleStudentChange()">
              <el-option v-for="s in studentOptions" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="合約(可選)" prop="student_contract_id">
            <el-select v-model="batchCreateForm.student_contract_id" filterable clearable placeholder="選擇合約" class="w-full" :disabled="!batchCreateForm.student_id" :loading="batchCreateDeps.isFetchingTeachers">
              <el-option v-for="c in batchCreateDeps.studentContractOptions" :key="c.id" :label="`${c.course_name} (${c.contract_no})`" :value="c.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="教師" prop="teacher_id">
            <el-select v-model="batchCreateForm.teacher_id" filterable placeholder="選擇教師" class="w-full" :disabled="!batchCreateForm.student_id" @change="batchCreateDeps.handleTeacherChange(false)" :loading="batchCreateDeps.isFetchingTeachers">
              <el-option v-for="t in batchCreateDeps.teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="課程" prop="course_id">
            <el-select v-model="batchCreateForm.course_id" filterable placeholder="選擇課程" class="w-full" :disabled="!batchCreateForm.student_id || !batchCreateForm.teacher_id" :loading="batchCreateDeps.isFetchingCourses">
              <el-option v-for="c in batchCreateDeps.courseOptions" :key="c.id" :label="c.course_name" :value="c.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="日期範圍" required>
          <el-date-picker 
            v-model="batchCreateForm.daterange" 
            type="daterange" 
            value-format="YYYY-MM-DD" 
            class="w-full!" />
        </el-form-item>
        <el-form-item label="上課時間">
          <div class="flex gap-2 w-full">
            <el-time-picker 
              v-model="batchCreateForm.start_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              placeholder="開始" 
              class="flex-1" />
            <span class="mt-1">-</span>
            <el-time-picker 
              v-model="batchCreateForm.end_time" 
              format="HH:mm" 
              value-format="HH:mm" 
              placeholder="結束" 
              class="flex-1" />
          </div>
        </el-form-item>
        <el-form-item label="星期幾">
          <el-checkbox-group v-model="batchCreateForm.weekdays">
            <el-checkbox :label="0">週一</el-checkbox><el-checkbox :label="1">週二</el-checkbox>
            <el-checkbox :label="2">週三</el-checkbox><el-checkbox :label="3">週四</el-checkbox>
            <el-checkbox :label="4">週五</el-checkbox><el-checkbox :label="5">週六</el-checkbox>
            <el-checkbox :label="6">週日</el-checkbox>
          </el-checkbox-group>
          <div class="text-xs text-gray-400 w-full mt-1">留空代表全選。</div>
        </el-form-item>
        <el-form-item label="備註">
          <el-input v-model="batchCreateForm.notes" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.batchCreate.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button 
          type="primary" 
          @click="submitBatchCreate" 
          :loading="dialogs.batchCreate.loading">建立</el-button>
      </template>
    </el-dialog>

    <!-- Periodic Batch Update -->
    <el-dialog 
      v-model="dialogs.batchUpdate.visible" 
      title="批次更新排課" 
      width="600px" 
      @closed="resetForm('batchUpdate')">
        <el-form :model="batchUpdateForm" :rules="batchUpdateRules" ref="batchUpdateRef" label-width="120px">
          <div class="font-bold mb-3 border-b pb-2">篩選條件</div>
          <el-form-item label="日期範圍" required>
            <el-date-picker 
              v-model="batchUpdateForm.daterange" 
              type="daterange" 
              value-format="YYYY-MM-DD" 
              class="w-full!" />
          </el-form-item>
          <el-form-item label="星期幾">
            <el-checkbox-group v-model="batchUpdateForm.weekdays">
              <el-checkbox :label="0">一</el-checkbox><el-checkbox :label="1">二</el-checkbox>
              <el-checkbox :label="2">三</el-checkbox><el-checkbox :label="3">四</el-checkbox>
              <el-checkbox :label="4">五</el-checkbox><el-checkbox :label="5">六</el-checkbox>
              <el-checkbox :label="6">日</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="學生">
            <el-select 
              v-model="batchUpdateForm.student_id" 
              filterable 
              clearable 
              placeholder="選擇學生(可選)" 
              class="w-full" 
              @change="batchUpdateDeps.handleStudentChange()">
              <el-option 
                v-for="s in studentOptions" 
                :key="s.id" 
                :label="s.name" 
                :value="s.id"/>
            </el-select>
          </el-form-item>
          <el-form-item label="教師">
            <el-select 
              v-model="batchUpdateForm.teacher_id" 
              filterable 
              clearable 
              placeholder="選擇教師" 
              class="w-full" 
              :disabled="!batchUpdateForm.student_id" 
              @change="batchUpdateDeps.handleTeacherChange(false)" 
              :loading="batchUpdateDeps.isFetchingTeachers">
              <el-option 
                v-for="t in batchUpdateDeps.teacherOptions" 
                :key="t.id" 
                :label="t.name" 
                :value="t.id"/>
            </el-select>
          </el-form-item>
          <el-form-item label="課程">
            <el-select 
              v-model="batchUpdateForm.course_id" 
              filterable 
              clearable 
              placeholder="選擇課程" 
              class="w-full" 
              :disabled="!batchUpdateForm.student_id || !batchUpdateForm.teacher_id" 
              :loading="batchUpdateDeps.isFetchingCourses">
              <el-option 
                v-for="c in batchUpdateDeps.courseOptions" 
                :key="c.id" 
                :label="c.course_name" 
                :value="c.id"/>
            </el-select>
          </el-form-item>
          <el-form-item label="原狀態">
            <el-select 
              v-model="batchUpdateForm.filter_status" 
              clearable 
              class="w-full">
              <el-option label="待確認" value="pending" /><el-option label="已確認" value="confirmed" />
              <el-option label="已完成" value="completed" /><el-option label="已取消" value="cancelled" />
            </el-select>
          </el-form-item>

          <div class="font-bold mb-3 mt-5 border-b pb-2">更新內容</div>
          <el-form-item label="新狀態" prop="new_status">
            <el-select 
              v-model="batchUpdateForm.new_status" 
              class="w-full">
              <el-option label="待確認" value="pending" /><el-option label="已確認" value="confirmed" />
              <el-option label="已完成" value="completed" /><el-option label="已取消" value="cancelled" />
            </el-select>
          </el-form-item>
          <el-form-item label="備註">
            <el-input v-model="batchUpdateForm.notes" type="textarea" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogs.batchUpdate.visible = false">{{ $t('common.cancel') }}</el-button>
          <el-button 
            type="primary" 
            @click="submitBatchUpdate" 
            :loading="dialogs.batchUpdate.loading">更新</el-button>
        </template>
    </el-dialog>

    <!-- Periodic Batch Delete -->
    <el-dialog 
      v-model="dialogs.batchDelete.visible" 
      title="批次刪除排課" 
      width="600px" 
      @closed="resetForm('batchDelete')">
        <el-form :model="batchDeleteForm" :rules="batchDeleteRules" ref="batchDeleteRef" label-width="120px">
          <el-form-item label="日期範圍" required>
              <el-date-picker 
                v-model="batchDeleteForm.daterange" 
                type="daterange" 
                value-format="YYYY-MM-DD" 
                class="w-full!" />
          </el-form-item>
          <el-form-item label="星期幾">
              <el-checkbox-group v-model="batchDeleteForm.weekdays">
                  <el-checkbox :label="0">一</el-checkbox><el-checkbox :label="1">二</el-checkbox>
                  <el-checkbox :label="2">三</el-checkbox><el-checkbox :label="3">四</el-checkbox>
                  <el-checkbox :label="4">五</el-checkbox><el-checkbox :label="5">六</el-checkbox>
                  <el-checkbox :label="6">日</el-checkbox>
              </el-checkbox-group>
          </el-form-item>
          <el-form-item label="學生">
              <el-select 
                v-model="batchDeleteForm.student_id" 
                filterable 
                clearable 
                placeholder="選擇學生(可選)" 
                class="w-full" 
                @change="batchDeleteDeps.handleStudentChange()">
                <el-option 
                  v-for="s in studentOptions" 
                  :key="s.id" 
                  :label="s.name" 
                  :value="s.id"/>
              </el-select>
          </el-form-item>
          <el-form-item label="教師">
              <el-select 
                v-model="batchDeleteForm.teacher_id" 
                filterable 
                clearable 
                placeholder="選擇教師" 
                class="w-full" 
                :disabled="!batchDeleteForm.student_id" 
                @change="batchDeleteDeps.handleTeacherChange(false)" 
                :loading="batchDeleteDeps.isFetchingTeachers">
                <el-option 
                  v-for="t in batchDeleteDeps.teacherOptions" 
                  :key="t.id" 
                  :label="t.name" 
                  :value="t.id"/>
              </el-select>
          </el-form-item>
          <el-form-item label="課程">
              <el-select 
                v-model="batchDeleteForm.course_id" 
                filterable 
                clearable 
                placeholder="選擇課程" 
                class="w-full" 
                :disabled="!batchDeleteForm.student_id || !batchDeleteForm.teacher_id" 
                :loading="batchDeleteDeps.isFetchingCourses">
                <el-option 
                  v-for="c in batchDeleteDeps.courseOptions" 
                  :key="c.id" 
                  :label="c.course_name" 
                  :value="c.id"/>
              </el-select>
          </el-form-item>
          <el-form-item label="狀態">
              <el-select 
                v-model="batchDeleteForm.filter_status" 
                clearable 
                class="w-full">
                <el-option label="待確認" value="pending" /><el-option label="已確認" value="confirmed" />
                <el-option label="已完成" value="completed" /><el-option label="已取消" value="cancelled" />
              </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogs.batchDelete.visible = false">{{ $t('common.cancel') }}</el-button>
          <el-button 
            type="danger" 
            @click="submitBatchDelete" 
            :loading="dialogs.batchDelete.loading">刪除</el-button>
        </template>
    </el-dialog>

    <el-dialog
      v-model="leaveDialogVisible"
      title="建立請假申請"
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
        <el-form-item label="請假原因" prop="reason">
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="4"
            maxlength="200"
            show-word-limit
            placeholder="請輸入請假原因" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="leaveDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="leaveSubmitting" @click="submitLeave">送出請假</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="substituteDialogVisible"
      title="指派代課"
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
        <el-form-item label="代課教師" prop="substitute_teacher_id">
          <el-select
            v-model="substituteForm.substitute_teacher_id"
            filterable
            class="w-full"
            placeholder="請選擇代課教師"
            :loading="substituteTeachersLoading">
            <el-option
              v-for="teacher in substituteTeacherOptions"
              :key="teacher.id"
              :label="`${teacher.teacher_no || ''}${teacher.teacher_no ? ' - ' : ''}${teacher.name}${teacher.is_preferred ? ' ★' : ''}`"
              :value="teacher.id" />
          </el-select>
        </el-form-item>

        <div v-if="substituteForm.substitute_teacher_id && substituteContractsLoading" class="mb-4 text-sm color-gray-500">
          正在確認代課教師合約...
        </div>
        <div
          v-else-if="substituteForm.substitute_teacher_id && !substituteForm.substitute_contract_id"
          class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm color-red-600">
          此代課教師目前沒有可用合約，無法指派代課。
        </div>

        <el-form-item label="代課原因" prop="reason">
          <el-input
            v-model="substituteForm.reason"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="請輸入代課原因（可選）" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="substituteDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="substituteSubmitting" @click="submitSubstitute">確認指派</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import dayjs from 'dayjs';
import {
  getBookingList, createBooking, updateBooking,
  batchCreateBookings, batchUpdateBookings, batchDeleteBookings,
  batchUpdateBookingsByIds, batchDeleteBookingsByIds,
  getBookingOptionSubstituteTeachers, getBookingOptionTeacherContracts,
  type BookingItem, type BookingListParams, type BookingStatus,
  type BookingSubstituteTeacherOption
} from '@/api/booking';
import { getZoomMeetingByBooking, createZoomMeeting, batchGetZoomMeetings, type ZoomMeetingLogResponse } from '@/api/zoom';
import { createLeaveRecord } from '@/api/leaveRecord';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { createSubstituteDetail, deleteSubstituteDetail } from '@/api/substituteDetail';
import { useBookingDependencies } from '@/composables/useBookingDependencies';
import { BOOKING_STATUS_MAP, BOOKING_TYPE_MAP } from '@/constants/booking';
import { copyToClipboardUtil } from '@/utils/clipboard';

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
    const res = assertApiSuccess(await getBookingList(params), '載入預約列表失敗');
    tableData.value = res.data;
    total.value = res.total;
    fetchZoomInfos();
  } catch (e: any) {
    ElMessage.error(getApiErrorMessage(e, '載入預約列表失敗'));
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
    const res = assertApiSuccess(await batchGetZoomMeetings(idsToFetch), '載入 Zoom 會議失敗');   
    if (res.data) {
      Object.entries(res.data).forEach(([bookingId, meeting]) => {                                                                                                  
        zoomInfoMap.value[bookingId] = meeting;
      });                                                                                                                                                           
    }                                                     
  } catch (e) {
    // batch 失敗時 fallback 到逐筆查詢                                                                                                                             
    await Promise.allSettled(
      idsToFetch.map(async (id) => {                                                                                                                                
        try {                                             
          const res = assertApiSuccess(await getZoomMeetingByBooking(id), '載入 Zoom 會議失敗');                                                                                                            
          if (res.data) zoomInfoMap.value[id] = res.data; 
        } catch { /* ignore */ }                                                                                                                                    
      })
    );                                                                                                                                                              
  }                                                       
};

const handleCreateZoom = async (row: BookingItem) => {
  creatingZoomMap.value[row.id] = true;
  try {
    const res = assertApiSuccess(await createZoomMeeting({ booking_id: row.id }), '建立會議失敗');
    if (res.data) zoomInfoMap.value[row.id] = res.data;
    ElMessage.success(res.message || '建立會議成功');
  } catch(e:any) {
    ElMessage.error(getApiErrorMessage(e, '建立會議失敗'));
  } finally {
    creatingZoomMap.value[row.id] = false;
  }
};

const copyToClipboard = (text: string | undefined | null) => {
  if (text) {
    copyToClipboardUtil(text, '密碼已複製');
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
  reason: [{ required: true, message: '請輸入請假原因', trigger: 'blur' }],
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
  substitute_teacher_id: [{ required: true, message: '請選擇代課教師', trigger: 'change' }],
};

const openLeaveDialog = (row: BookingItem) => {
  if (row.booking_status !== 'confirmed') {
    ElMessage.warning('只有已確認的預約可以請假');
    return;
  }
  if (row.has_pending_leave) {
    ElMessage.warning('此預約已有待審核的請假申請');
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
      await ElMessageBox.confirm('送出後將建立請假申請，確定繼續嗎？', '確認請假', {
        confirmButtonText: '送出請假',
        cancelButtonText: '取消',
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
      }), '送出請假失敗');

      ElMessage.success(res.message || '請假申請已送出');
      leaveDialogVisible.value = false;
      fetchData();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '送出請假失敗'));
    } finally {
      leaveSubmitting.value = false;
    }
  });
};

const loadSubstituteTeacherOptions = async (bookingId: string) => {
  substituteTeachersLoading.value = true;
  try {
    const res = assertApiSuccess(await getBookingOptionSubstituteTeachers(bookingId), '載入代課教師失敗');
    substituteTeacherOptions.value = res.data || [];
  } catch (error) {
    substituteTeacherOptions.value = [];
    ElMessage.error(getApiErrorMessage(error, '載入代課教師失敗'));
  } finally {
    substituteTeachersLoading.value = false;
  }
};

const openSubstituteDialog = async (row: BookingItem) => {
  if (row.booking_status !== 'confirmed') {
    ElMessage.warning('只有已確認的預約可以指派代課');
    return;
  }
  if (row.substitute_detail_id) {
    ElMessage.warning('此預約已有代課安排');
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
      const res = assertApiSuccess(await getBookingOptionTeacherContracts(teacherId), '載入教師合約失敗');
      const [firstContract] = res.data || [];
      if (firstContract) {
        substituteForm.substitute_contract_id = firstContract.id;
      } else {
        ElMessage.warning('此代課教師目前沒有可用合約');
      }
    } catch (error) {
      substituteForm.substitute_contract_id = '';
      ElMessage.error(getApiErrorMessage(error, '載入教師合約失敗'));
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
      ElMessage.warning('此代課教師目前沒有可用合約');
      return;
    }

    substituteSubmitting.value = true;
    try {
      const res = assertApiSuccess(await createSubstituteDetail({
        booking_id: substituteBooking.value.id,
        substitute_teacher_id: substituteForm.substitute_teacher_id,
        substitute_contract_id: substituteForm.substitute_contract_id,
        reason: substituteForm.reason.trim() || null,
      }), '指派代課失敗');

      ElMessage.success(res.message || '代課已指派');
      substituteDialogVisible.value = false;
      fetchData();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '指派代課失敗'));
    } finally {
      substituteSubmitting.value = false;
    }
  });
};

const handleCancelSubstitute = async (row: BookingItem) => {
  if (!row.substitute_detail_id) {
    ElMessage.warning('此預約目前沒有代課安排');
    return;
  }

  try {
    await ElMessageBox.confirm(
      `確定要取消「${row.booking_no}」的代課安排嗎？取消後預約狀態將改回待確認。`,
      '取消代課',
      {
        confirmButtonText: '確認取消',
        cancelButtonText: '返回',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  try {
    const res = assertApiSuccess(await deleteSubstituteDetail(row.substitute_detail_id), '取消代課失敗');
    ElMessage.success(res.message || '代課已取消');
    fetchData();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '取消代課失敗'));
  }
};

const handleCancelBooking = async (row: BookingItem) => {
  try {
    await ElMessageBox.confirm(`確定要取消「${row.booking_no}」嗎？`, '取消預約', {
      confirmButtonText: '下一步',
      cancelButtonText: '返回',
      type: 'warning',
    });
  } catch {
    return;
  }

  try {
    await ElMessageBox.confirm('取消後將同步取消相關會議與行事曆資料，是否再次確認？', '再次確認', {
      confirmButtonText: '確認取消',
      cancelButtonText: '保留預約',
      type: 'error',
    });
  } catch {
    return;
  }

  try {
    const res = assertApiSuccess(await updateBooking(row.id, {
      booking_status: 'cancelled',
    }), '取消預約失敗');

    ElMessage.success(res.message || '預約已取消');
    fetchData();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '取消預約失敗'));
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
  if(name === 'add') { addFormRef.value?.resetFields(); addDeps.resetOptions(); }
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
  timeMode: 'manual', booking_date: '', start_time: '', end_time: '', teacher_slot_id: '', notes: ''
});
const addDeps = reactive(useBookingDependencies(addForm, addFormRef));

const validateBookingDate = (_rule: any, value: any, callback: any) => {
  if (addForm.timeMode === 'manual' && !value) callback(new Error('必填'));
  else callback();
};

const addRules: FormRules = {
  student_id: [{ required: true, message: '必填', trigger: 'change' }],
  teacher_id: [{ required: true, message: '必填', trigger: 'change' }],
  course_id: [{ required: true, message: '必填', trigger: 'change' }],
  booking_date: [{ validator: validateBookingDate, trigger: 'change' }]
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
          ElMessage.warning('請填寫完整時間');
          dialogs.add.loading = false;
          return;
        }
        data.start_time = addForm.start_time.substring(0,5); data.end_time = addForm.end_time.substring(0,5);
      } else {
        if(!addForm.teacher_slot_id) {
          ElMessage.warning('請選擇教師時段');
          dialogs.add.loading = false;
          return;
        }
        const slot = addDeps.teacherSlotOptions.find(s=>s.id === addForm.teacher_slot_id);
        data.teacher_slot_id = addForm.teacher_slot_id;
        data.booking_date = slot?.slot_date;
        data.start_time = slot?.start_time.substring(0,5);
        data.end_time = slot?.end_time.substring(0,5);
      }
      const res = assertApiSuccess(await createBooking(data), '新增失敗');
      ElMessage.success(res.message || '新增成功');
      dialogs.add.visible = false;
      fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '新增失敗')); }
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
const editRules: FormRules = { booking_status: [{ required: true, message: '必填' }] };
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
      }), '更新失敗');
      ElMessage.success(res.message || '更新成功');
      dialogs.edit.visible = false;
      fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '更新失敗')); }
    finally { dialogs.edit.loading = false; }
  });
};

// Batch Update By IDs Dialog
const batchUpdateByIdsRef = ref<FormInstance>();
const batchUpdateByIdsForm = reactive({ booking_status: 'confirmed' as BookingStatus, notes: '' });
const submitBatchUpdateByIds = async () => {
  dialogs.batchUpdateByIds.loading = true;
  try {
    const res = assertApiSuccess(await batchUpdateBookingsByIds({ booking_ids: selectedIds.value, booking_status: batchUpdateByIdsForm.booking_status, notes: batchUpdateByIdsForm.notes || null }), '操作失敗');
    ElMessage.success(res.message || '批次更新成功');
    dialogs.batchUpdateByIds.visible = false;
    selectedIds.value = [];
    fetchData();
  } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '操作失敗')); }
  finally { dialogs.batchUpdateByIds.loading = false; }
};

// Batch Delete By IDs
const handleDelete = (row: BookingItem) => {
  ElMessageBox.confirm('確定要永久刪除此筆記錄？', '刪除', { type: 'error' }).then(async () => {
    try {
      const res = assertApiSuccess(await batchDeleteBookingsByIds({ booking_ids: [row.id] }), '刪除失敗');
      ElMessage.success(res.message || '已刪除');
      fetchData();
    }
    catch(e:any) { ElMessage.error(getApiErrorMessage(e, '刪除失敗')); }
  });
};
const handleBatchDeleteByIds = () => {
  ElMessageBox.confirm(`確定要永久刪除選取的 ${selectedIds.value.length} 筆記錄？`, '批次刪除', { type: 'error' }).then(async () => {
    try {
      const res = assertApiSuccess(await batchDeleteBookingsByIds({ booking_ids: selectedIds.value }), '刪除失敗');
      ElMessage.success(res.message || '已刪除');
      selectedIds.value = [];
      fetchData();
    }
    catch(e:any) { ElMessage.error(getApiErrorMessage(e, '刪除失敗')); }
  });
};

// Periodic Batch Create Dialog
const batchCreateRef = ref<FormInstance>();
const batchCreateForm = reactive({ student_id:'', student_contract_id: '', teacher_id:'', course_id:'', daterange: [] as any[], weekdays: [] as number[], start_time:'', end_time:'', notes:'' });
const batchCreateDeps = reactive(useBookingDependencies(batchCreateForm, batchCreateRef));
const batchCreateRules: FormRules = {
    student_id: [{ required: true, message: '必填' }], teacher_id: [{ required: true, message: '必填' }], course_id: [{ required: true, message: '必填' }]
};
const submitBatchCreate = async () => {
  if(!batchCreateRef.value) return;
  await batchCreateRef.value.validate(async v => {
    if(!v || !batchCreateForm.daterange || batchCreateForm.daterange.length !== 2) { if(!v) return; ElMessage.warning('需要日期範圍'); return; }
    dialogs.batchCreate.loading = true;
    try {
      const res = assertApiSuccess(await batchCreateBookings({
        student_id: batchCreateForm.student_id, teacher_id: batchCreateForm.teacher_id, course_id: batchCreateForm.course_id,
        student_contract_id: batchCreateForm.student_contract_id || null,
        start_date: batchCreateForm.daterange[0], end_date: batchCreateForm.daterange[1],
        weekdays: batchCreateForm.weekdays.length > 0 ? batchCreateForm.weekdays : null,
        start_time: batchCreateForm.start_time.substring(0,5) || null, end_time: batchCreateForm.end_time.substring(0,5) || null, notes: batchCreateForm.notes || null,
      }), '建立失敗');
      ElMessage.success(res.message || '批次建立成功'); dialogs.batchCreate.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '建立失敗')); }
    finally { dialogs.batchCreate.loading = false; }
  });
};

// Periodic Batch Update Dialog
const batchUpdateRef = ref<FormInstance>();
const batchUpdateForm = reactive({ daterange: [] as any[], weekdays: [] as number[], student_id:'', teacher_id:'', course_id:'', filter_status:'' as any, new_status:'confirmed' as any, notes:'' });
const batchUpdateDeps = reactive(useBookingDependencies(batchUpdateForm, batchUpdateRef));
const batchUpdateRules: FormRules = { new_status: [{ required: true, message: '必填' }] };
const submitBatchUpdate = async () => {
  if(!batchUpdateRef.value) return;
  await batchUpdateRef.value.validate(async v => {
    if(!v || !batchUpdateForm.daterange || batchUpdateForm.daterange.length !== 2) { if(!v) return; ElMessage.warning('需要日期範圍'); return; }
    dialogs.batchUpdate.loading = true;
    try {
      const res = assertApiSuccess(await batchUpdateBookings({
        start_date: batchUpdateForm.daterange[0], end_date: batchUpdateForm.daterange[1],
        weekdays: batchUpdateForm.weekdays.length > 0 ? batchUpdateForm.weekdays : null,
        student_id: batchUpdateForm.student_id || null, teacher_id: batchUpdateForm.teacher_id || null, course_id: batchUpdateForm.course_id || null,
        filter_status: batchUpdateForm.filter_status || null, new_status: batchUpdateForm.new_status, notes: batchUpdateForm.notes || null
      }), '更新失敗');
      ElMessage.success(res.message || '批次更新成功'); dialogs.batchUpdate.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '更新失敗')); }
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
    if(!v || !batchDeleteForm.daterange || batchDeleteForm.daterange.length !== 2) { if(!v) return; ElMessage.warning('需要日期範圍'); return; }
    dialogs.batchDelete.loading = true;
    try {
      const res = assertApiSuccess(await batchDeleteBookings({
        start_date: batchDeleteForm.daterange[0], end_date: batchDeleteForm.daterange[1],
        weekdays: batchDeleteForm.weekdays.length > 0 ? batchDeleteForm.weekdays : null,
        student_id: batchDeleteForm.student_id || null, teacher_id: batchDeleteForm.teacher_id || null, course_id: batchDeleteForm.course_id || null,
        filter_status: batchDeleteForm.filter_status || null
      }), '刪除失敗');
      ElMessage.success(res.message || '批次刪除成功'); dialogs.batchDelete.visible = false; fetchData();
    } catch(e:any) { ElMessage.error(getApiErrorMessage(e, '刪除失敗')); }
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
</style>
