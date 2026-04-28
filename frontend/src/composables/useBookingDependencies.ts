// src/composables/useBookingDependencies.ts
import { ref, type Ref } from 'vue';
import type { FormInstance } from 'element-plus';
import dayjs from 'dayjs';
import { assertApiSuccess } from '@/api/response';
import {
  getBookingOptionStudents,
  getBookingOptionTeachers,
  getBookingCourseOptions,
  getBookingOptionStudentContracts,
  getBookingOptionTeacherSlots,
  getBookingOptionOverlappingCourses,
  type BookingStudentOption,
  type BookingTeacherOption,
  type BookingCourseOption,
  type BookingStudentContractOption,
  type BookingTeacherSlotOption
} from '@/api/booking';

// Optional: Global cache for root options if they don't depend on user selection
const globalStudentOptions = ref<BookingStudentOption[]>([]);
const globalTeacherOptions = ref<BookingTeacherOption[]>([]);
const globalCourseOptions = ref<BookingCourseOption[]>([]);
let isGlobalLoaded = false;

export function useBookingDependencies(formData: any, formRef?: Ref<FormInstance | undefined>) {
  const studentOptions = ref<BookingStudentOption[]>([]);
  const teacherOptions = ref<BookingTeacherOption[]>([]);
  const courseOptions = ref<BookingCourseOption[]>([]);
  const studentContractOptions = ref<BookingStudentContractOption[]>([]);
  const teacherSlotOptions = ref<BookingTeacherSlotOption[]>([]);

  const isFetchingStudents = ref(false);
  const isFetchingTeachers = ref(false);
  const isFetchingCourses = ref(false);

  // Initial load for global options
  const loadInitialOptions = async () => {
    if (!isGlobalLoaded) {
      isFetchingStudents.value = true;
      try {
        const [sRes, tRes, cRes] = await Promise.all([
          getBookingOptionStudents(), getBookingOptionTeachers(), getBookingCourseOptions()
        ]);
        globalStudentOptions.value = assertApiSuccess(sRes).data || [];
        globalTeacherOptions.value = assertApiSuccess(tRes).data || [];
        globalCourseOptions.value = assertApiSuccess(cRes).data || [];
        isGlobalLoaded = true;
      } catch (e) {
        console.error(e);
      } finally {
        isFetchingStudents.value = false;
      }
    }
    studentOptions.value = globalStudentOptions.value;
    // For filters, you might want to expose global teachers/courses
    // but for cascading forms, these start empty or disabled.
  };

  const handleStudentChange = async () => {
    formData.teacher_id = null;
    formData.course_id = null;
    if ('student_contract_id' in formData) formData.student_contract_id = null;
    if ('teacher_slot_id' in formData) formData.teacher_slot_id = null;

    setTimeout(() => {
      if (formRef && formRef.value) {
        formRef.value.clearValidate(['teacher_id', 'course_id', 'student_contract_id', 'teacher_slot_id']);
      }
    }, 10);

    teacherOptions.value = [];
    studentContractOptions.value = [];
    courseOptions.value = [];
    teacherSlotOptions.value = [];

    if (!formData.student_id) return;

    isFetchingTeachers.value = true;
    try {
      const [tRes, cRes] = await Promise.all([
        getBookingOptionTeachers({ student_id: formData.student_id }),
        getBookingOptionStudentContracts(formData.student_id)
      ]);
      teacherOptions.value = assertApiSuccess(tRes).data || [];
      studentContractOptions.value = assertApiSuccess(cRes).data || [];
    } catch (e) {
      console.error(e);
    } finally {
      isFetchingTeachers.value = false;
    }
  };

  const handleTeacherChange = async (needsSlot: boolean = false) => {
    formData.course_id = null;
    if ('teacher_slot_id' in formData) formData.teacher_slot_id = null;

    setTimeout(() => {
      if (formRef && formRef.value) {
        formRef.value.clearValidate(['course_id', 'teacher_slot_id']);
      }
    }, 10);

    courseOptions.value = [];
    teacherSlotOptions.value = [];

    if (!formData.student_id || !formData.teacher_id) return;

    isFetchingCourses.value = true;
    try {
      const tasks: Promise<any>[] = [
        getBookingOptionOverlappingCourses({ student_id: formData.student_id, teacher_id: formData.teacher_id })
      ];
      if (needsSlot) {
        tasks.push(getBookingOptionTeacherSlots(formData.teacher_id, {
          date_from: dayjs().format('YYYY-MM-DD'),
        }));
      }

      const results = await Promise.all(tasks);
      courseOptions.value = assertApiSuccess(results[0]).data || [];
      if (needsSlot && results.length > 1) {
        teacherSlotOptions.value = assertApiSuccess(results[1]).data || [];
      }
    } catch (e) {
      console.error(e);
    } finally {
      isFetchingCourses.value = false;
    }
  };

  const resetOptions = () => {
    teacherOptions.value = [];
    courseOptions.value = [];
    studentContractOptions.value = [];
    teacherSlotOptions.value = [];
  };

  return {
    studentOptions,
    teacherOptions,
    courseOptions,
    studentContractOptions,
    teacherSlotOptions,
    isFetchingStudents,
    isFetchingTeachers,
    isFetchingCourses,
    handleStudentChange,
    handleTeacherChange,
    loadInitialOptions,
    resetOptions,
    globalTeacherOptions,
    globalCourseOptions
  };
}
