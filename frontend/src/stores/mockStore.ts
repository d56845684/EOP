import { defineStore } from 'pinia';
import dayjs from 'dayjs';
import { ElMessage } from 'element-plus';

// --- Types ---

// export type Role = 'admin' | 'super_admin'; // Deprecated

export interface PermissionNode {
  id: string;
  label: string;
  children?: PermissionNode[];
}

export interface RoleDef {
  id: string;
  name: string;
  note: string;
  status: boolean;
  permissions: string[]; // List of permission node IDs
  updatedAt: string;
}

export interface User {
  id: string;
  username: string;
  password?: string; // Only for initial mock, ideally hashed or hidden
  nickname: string;
  avatar: string;
  role: string; // Changed from Role to string to support dynamic roles
  status: boolean; // true = active
  createdAt: string;
  permissions?: string[]; // RBAC
}

export interface Course {
  id: string;
  code: string; // New field
  name: string;
  description: string;
  duration: number; // minutes
  price: number;
  cover: string;
  defaultTeacherId?: string;
}

export type ContractType = 'Full-time' | 'Part-time';

export interface SalaryConfig {
  baseSalary?: number; // Full-time
  overtimeRate?: number; // Full-time
  hourlyRate?: number; // Part-time
  courseRates?: { courseId: string; price: number }[]; // Part-time specific rates
}

export interface Teacher {
  id: string;
  name: string;
  description: string;
  contractType: ContractType;
  bonusMultiplier: number; // e.g., 1.25
  salaryConfig: SalaryConfig;
  status: boolean; // Off-shelf logic
  avatar?: string;
  // New Fields
  email: string;
  phone: string;
  zoomLink: string;
  tags: string[]; // specific tags (optional, keeping for compat)
  bio?: string;
  videoUrl?: string;
  certs?: string[];
  // Fee Settings
  isCourseFeesEnabled?: boolean;
  courseFees?: { courseId: string; price: number }[];
  // Resume / Bio
  courseIds?: string[]; // List of authorized course IDs
  educationExperience?: string;
  teachingSpecialty?: string;
  introduction?: string;
}

export type StudentType = 'Trial' | 'Regular';

export interface Student {
  id: string;
  name: string;
  engName: string; // New
  birthday: string; // New
  email: string; // New - explicitly asked in table
  phone: string; // New - explicitly asked in table
  address: string; // New
  emergencyContactName: string; // New
  emergencyContactPhone: string; // New
  contractId: string; // New
  contractPeriod: [string, string]; // New [start, end]
  contractFileUrl?: string; // New
  leaveLimit: number; // New
  note: string; // New
  type: StudentType;

  // Booking System Fields
  lateCancelCount: number;
  maxLateCancel: number;
  contractUrl?: string; // Deprecated by contractFileUrl? keeping for compat
  credits: number;
  purchasedCourses: { courseId: string; date: string }[];
  avatar?: string;
  updatedAt: string; // For "Last Updated"
}

export type BookingStatus = 'Scheduled' | 'Completed' | 'Cancelled';

export interface Booking {
  id: string;
  time: string; // ISO string
  studentId: string;
  teacherId: string;
  courseId: string;
  type: StudentType; // Tied to student type at time of booking usually, or class type
  status: BookingStatus;
  isConverted: boolean; // For Trial classes: verified conversion?
  createdAt: string;
  duration?: number; // New: standard 50-60min
  link?: string;     // New: Zoom/Meeting link
  note?: string;     // New: Notes
  noteUrl?: string;  // New: After-class note URL
}

export interface TeacherSlot {
  id: string;
  teacherId: string;
  start: string; // ISO string 2025-12-25T09:00:00
  end: string;   // ISO string 2025-12-25T09:30:00
  status: 'Available' | 'Booked' | 'Leave';
  bookingId?: string; // Linked booking if Booked
}

// --- State Interface ---

interface MockState {
  users: User[];
  teachers: Teacher[];
  students: Student[];
  courses: Course[];
  bookings: Booking[];
  teacherSlots: TeacherSlot[]; // New
  roles: RoleDef[];
  currentUser: User | null;
}

// --- System Modules (Unified Menu & Permissions) ---

export interface SystemModule {
  id: string;
  label: string;
  icon?: string; // Icon name for sidebar
  path?: string; // Route path if it's a direct link (usually pages)
  children?: SystemModule[];
}

export const SYSTEM_MODULES: SystemModule[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: 'Odometer',
    path: '/dashboard',
    children: [
      {
        id: 'dashboard_page',
        label: 'Dashboard',
        children: [
          { id: 'dashboard_page:view', label: 'View' },
          { id: 'dashboard_page:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'reports',
    label: 'Report Statistics',
    icon: 'DataLine',
    path: '/reports',
    children: [
      {
        id: 'reports_page',
        label: 'Reports',
        children: [
          { id: 'reports_page:view', label: 'View' },
          { id: 'reports_page:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'teacher_mgmt',
    label: 'Teacher Management',
    icon: 'User',
    path: '/teacher',
    children: [
      {
        id: 'teachers',
        label: 'Teachers',
        path: '/teacher',
        children: [
          { id: 'teachers:view', label: 'View' },
          { id: 'teachers:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'student_mgmt',
    label: 'Student Management',
    icon: 'School',
    path: '/student',
    children: [
      {
        id: 'students',
        label: 'Students List',
        path: '/student',
        children: [
          { id: 'students:view', label: 'View' },
          { id: 'students:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'booking_mgmt',
    label: 'Booking Management',
    icon: 'Calendar',
    path: '/booking',
    children: [
      {
        id: 'bookings',
        label: 'Bookings List',
        path: '/booking',
        children: [
          { id: 'bookings:view', label: 'View' },
          { id: 'bookings:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'course_mgmt',
    label: 'Course Management',
    icon: 'Reading',
    path: '/course',
    children: [
      {
        id: 'courses',
        label: 'Course List',
        path: '/course',
        children: [
          { id: 'courses:view', label: 'View' },
          { id: 'courses:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'financial_mgmt',
    label: 'Financial Management',
    icon: 'Money',
    path: '/salary',
    children: [
      {
        id: 'salary',
        label: 'Salary Reports',
        path: '/salary',
        children: [
          { id: 'salary:view', label: 'View' },
          { id: 'salary:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'settings_mgmt',
    label: 'Settings',
    icon: 'Setting',
    children: [
      {
        id: 'account_settings',
        label: 'Account Management',
        path: '/settings/account',
        children: [
          { id: 'account_settings:view', label: 'View' },
          { id: 'account_settings:edit', label: 'Edit' }
        ]
      },
      {
        id: 'role_settings',
        label: 'Role Settings',
        path: '/settings/role',
        children: [
          { id: 'role_settings:view', label: 'View' },
          { id: 'role_settings:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'teacher_portal',
    label: 'Teacher Portal',
    icon: 'Avatar',
    children: [
      {
        id: 'schedule_settings',
        label: 'Schedule Settings',
        path: '/teacher-portal/schedule',
        children: [
          { id: 'schedule_settings:view', label: 'View' },
          { id: 'schedule_settings:edit', label: 'Edit' }
        ]
      },
      {
        id: 'booking_history',
        label: 'Booking History',
        path: '/teacher-portal/history',
        children: [
          { id: 'booking_history:view', label: 'View' }
        ]
      },
      {
        id: 'teacher_profile',
        label: 'Profile',
        path: '/teacher-portal/profile',
        children: [
          { id: 'teacher_profile:view', label: 'View' },
          { id: 'teacher_profile:edit', label: 'Edit' }
        ]
      }
    ]
  },
  {
    id: 'student_portal',
    label: 'Student Portal',
    icon: 'Avatar',
    children: [
      {
        id: 'class_booking',
        label: 'Class Booking',
        path: '/student-portal/booking',
        children: [
          { id: 'class_booking:view', label: 'View' },
          { id: 'class_booking:edit', label: 'Edit' }
        ]
      },
      {
        id: 'student_profile',
        label: 'Profile',
        path: '/student-portal/profile',
        children: [
          { id: 'student_profile:view', label: 'View' },
          { id: 'student_profile:edit', label: 'Edit' }
        ]
      }
    ]
  }
];

export const PERMISSION_TREE_DATA = SYSTEM_MODULES;

// --- Seed Data ---

const SEED_USERS: User[] = [
  {
    id: 'u1',
    username: 'eopAdmin',
    password: 'eopsuper888',
    nickname: 'Super Admin',
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    role: 'super_admin',
    status: true,
    createdAt: dayjs().subtract(1, 'year').toISOString(),
  },
  {
    id: 'u2',
    username: 'teacher.a',
    password: '123456',
    nickname: 'Teacher A',
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    role: 'teacher',
    status: true,
    createdAt: dayjs().subtract(6, 'month').toISOString(),
  },
  {
    id: 'u3',
    username: 'student.a',
    password: '123456',
    nickname: 'Student A',
    avatar: 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png',
    role: 'student',
    status: true,
    createdAt: dayjs().subtract(3, 'month').toISOString(),
  },
];

const SEED_ROLES: RoleDef[] = [
  {
    id: 'super_admin',
    name: 'Super Admin',
    note: 'System Administrator with full access. Cannot be deleted.',
    status: true,
    permissions: SYSTEM_MODULES.flatMap(m => {
      // Exclude Portal modules from Super Admin by default
      if (['teacher_portal', 'student_portal'].includes(m.id)) return [];

      return m.children?.flatMap(p =>
        p.children?.map(a => a.id) || []
      ) || [];
    }),
    updatedAt: dayjs().subtract(1, 'year').toISOString(),
  },
  {
    id: 'r2',
    name: 'Teacher Manager',
    note: 'Manages teacher resources only.',
    status: true,
    permissions: ['teachers:view', 'teachers:edit'],
    updatedAt: dayjs().subtract(5, 'day').toISOString(),
  },
  {
    id: 'teacher',
    name: 'Teacher',
    note: 'Standard Teacher Role',
    status: true,
    permissions: [
      'schedule_settings:view', 'schedule_settings:edit',
      'booking_history:view',
      'teacher_profile:view', 'teacher_profile:edit'
    ],
    updatedAt: dayjs().toISOString(),
  },
  {
    id: 'student',
    name: 'Student',
    note: 'Standard Student Role',
    status: true,
    permissions: [
      'class_booking:view', 'class_booking:edit',
      'student_profile:view', 'student_profile:edit'
    ],
    updatedAt: dayjs().toISOString(),
  }
];

const SEED_COURSES: Course[] = [
  {
    id: 'c1',
    code: 'C001',
    name: 'General English',
    description: 'Basic communication skills.',
    duration: 60,
    price: 500,
    cover: '',
    defaultTeacherId: 't1',
  },
  {
    id: 'c2',
    code: 'C002',
    name: 'Business English',
    description: 'For professionals.',
    duration: 60,
    price: 800,
    cover: '',
    defaultTeacherId: 't2',
  }
];

const SEED_TEACHERS: Teacher[] = [
  {
    id: 't1',
    name: 'Teacher A',
    description: 'Senior English Instructor',
    contractType: 'Part-time',
    bonusMultiplier: 2.0,
    salaryConfig: {
      hourlyRate: 500,
      courseRates: [],
    },
    status: true,
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    email: 'teacher.a@example.com',
    phone: '0912345678',
    zoomLink: 'https://zoom.us/j/1234567890',
    tags: ['IELTS'],
    bio: 'Experienced in IELTS and TOEFL preparation.',
    certs: ['cert_tefl.pdf'],
    courseIds: ['c1', 'c2']
  },
  {
    id: 't2',
    name: 'Teacher B (Full-time)',
    description: 'Junior Instructor',
    contractType: 'Full-time',
    bonusMultiplier: 1.0,
    salaryConfig: {
      baseSalary: 35000,
      overtimeRate: 300
    },
    status: true,
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    email: 'teacher.b@example.com',
    phone: '0912345678',
    zoomLink: 'https://zoom.us/j/1234567890',
    tags: ['TOEFL'],
    bio: 'Experienced in TOEFL preparation.',
    certs: ['cert_toefl.pdf'],
    courseIds: ['c1', 'c2']
  }
];

const SEED_BOOKINGS: Booking[] = [
  {
    id: 'b1',
    time: dayjs().subtract(1, 'hour').toISOString(),
    studentId: 's1', // Student B
    teacherId: 't1', // Teacher A (Default for C1) -> Regular
    courseId: 'c1',
    type: 'Trial',
    status: 'Completed',
    isConverted: false, // Unverified
    createdAt: dayjs().subtract(2, 'day').toISOString(),
    noteUrl: 'https://example.com/notes/b1.pdf'
  },
  {
    id: 'b2',
    time: dayjs().subtract(2, 'hour').toISOString(),
    studentId: 's2', // Student C
    teacherId: 't2', // Teacher B teaching C1 (Default is T1) -> Substitute!
    courseId: 'c1',
    type: 'Regular',
    status: 'Completed',
    isConverted: true,
    createdAt: dayjs().subtract(3, 'day').toISOString(),
    // Missing noteUrl to test "Update Note"
  },
  {
    id: 'b3',
    time: dayjs().add(1, 'day').toISOString(), // Future
    studentId: 's2',
    teacherId: 't1', // Teacher A
    courseId: 'c2',
    type: 'Regular',
    status: 'Scheduled',
    isConverted: false,
    createdAt: dayjs().toISOString(),
  }
];
// Correction on Booking 2: Teacher B teaches Course 1 (where default is T1). Ideally this should show Substitute.

const SEED_STUDENTS: Student[] = [
  {
    id: 's1',
    name: 'Student B',
    engName: 'Bob',
    birthday: '2010-05-20',
    email: 'student.b@example.com',
    phone: '0912345678',
    address: '123 Main St, Taipei',
    emergencyContactName: 'Parent B',
    emergencyContactPhone: '0987654321',
    contractId: 'CT-2025-001',
    contractPeriod: ['2025-01-01', '2025-12-31'],
    contractFileUrl: '',
    leaveLimit: 2,
    note: 'Interested in speaking classes.',
    type: 'Trial',
    lateCancelCount: 0,
    maxLateCancel: 3,
    credits: 0,
    purchasedCourses: [],
    updatedAt: dayjs().toISOString(),
  },
  {
    id: 's2',
    name: 'Student C',
    engName: 'Charlie',
    birthday: '2012-08-15',
    email: 'student.c@example.com',
    phone: '0912345678',
    address: '456 Second St, Taipei',
    emergencyContactName: 'Parent C',
    emergencyContactPhone: '0987654321',
    contractId: 'CT-2025-002',
    contractPeriod: ['2025-06-01', '2026-05-31'],
    contractFileUrl: '',
    leaveLimit: 3,
    note: 'Good progress.',
    type: 'Regular',
    lateCancelCount: 1,
    maxLateCancel: 3,
    credits: 10,
    purchasedCourses: [{ courseId: 'c1', date: '2025-06-01' }],
    updatedAt: dayjs().subtract(1, 'week').toISOString(),
  }
];

// --- Helper for Delay ---
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const MOCK_DELAY = 800;

export const useMockStore = defineStore('mock', {
  state: (): MockState => ({
    users: SEED_USERS,
    teachers: SEED_TEACHERS,
    students: SEED_STUDENTS,
    courses: SEED_COURSES,
    bookings: SEED_BOOKINGS,
    teacherSlots: [], // Initialize empty, or add seed data if needed
    roles: SEED_ROLES,
    currentUser: null,
  }),
  persist: {
    key: 'eop_store_v2', // Versioned to reset state with new accounts
    storage: localStorage,
  },
  actions: {
    // --- Teacher Schedule Slots ---
    async fetchSlots(teacherId: string, start: string, end: string) {
      await delay(300); // Small delay
      // Filter slots within range
      return this.teacherSlots.filter(s =>
        s.teacherId === teacherId &&
        s.start >= start &&
        s.end <= end
      );
    },

    async addSlot(slot: TeacherSlot) {
      await delay(300);
      this.teacherSlots.push(slot);
    },

    async removeSlot(slotId: string) {
      await delay(300);
      this.teacherSlots = this.teacherSlots.filter(s => s.id !== slotId);
    },

    async updateSlotStatus(slotId: string, status: 'Available' | 'Booked' | 'Leave', bookingId?: string) {
      await delay(300);
      const slot = this.teacherSlots.find(s => s.id === slotId);
      if (slot) {
        slot.status = status;
        if (bookingId !== undefined) slot.bookingId = bookingId;
      }
    },

    // --- Auth ---
    async login(username: string, pass: string) {
      await delay(MOCK_DELAY);
      const user = this.users.find(
        (u) => u.username === username && u.password === pass
      );
      if (user) {
        if (!user.status) throw new Error('Account is disabled');

        // RBAC: Attach permissions
        const userRole = this.roles.find(r => r.id === user.role);
        const permissions = userRole ? userRole.permissions : [];

        this.currentUser = { ...user, permissions };

        // Persist to local storage for prototype refresh happiness
        localStorage.setItem('eop_user', JSON.stringify(this.currentUser));

        return user;
      }
      throw new Error('Invalid credentials');
    },

    async logout() {
      this.currentUser = null;
    },

    // --- Teachers ---
    async fetchTeachers() {
      await delay(500);
      return this.teachers;
    },
    async saveTeacher(teacher: Teacher) {
      await delay(MOCK_DELAY);
      const idx = this.teachers.findIndex((t) => t.id === teacher.id);
      if (idx > -1) {
        this.teachers[idx] = teacher;
      } else {
        this.teachers.push({ ...teacher, id: 't' + Date.now() });
      }
    },
    async deleteTeacher(id: string) {
      await delay(MOCK_DELAY);
      this.teachers = this.teachers.filter((t) => t.id !== id);
    },
    async toggleTeacherStatus(id: string, active: boolean) {
      await delay(MOCK_DELAY);
      const t = this.teachers.find((x) => x.id === id);
      if (t) {
        t.status = active;
        if (!active) {
          // Off-shelf logic: Cancel future bookings
          const now = dayjs().toISOString();
          this.bookings.forEach((b) => {
            if (b.teacherId === id && b.status === 'Scheduled' && b.time > now) {
              b.status = 'Cancelled';
            }
          });
          ElMessage.warning('Teacher off-shelved. Future bookings cancelled.');
        }
      }
    },

    // --- bookings ---
    async checkConflict(time: string, teacherId: string, durationMin: number) {
      // Simple overlap check
      const start = dayjs(time);
      const end = start.add(durationMin, 'minute');

      const hasConflict = this.bookings.some(b => {
        if (b.teacherId !== teacherId || b.status === 'Cancelled') return false;
        // Assume all courses are 60 mins for simplicity unless we look up course
        // But we should look up course duration.
        // For conflict check, we'll assume the checked slot vs existing slots.
        // We need to know existing slot durations.
        const bCourse = this.courses.find(c => c.id === b.courseId);
        const bDur = bCourse ? bCourse.duration : 60;
        const bStart = dayjs(b.time);
        const bEnd = bStart.add(bDur, 'minute');

        return (start.isBefore(bEnd) && end.isAfter(bStart));
      });
      return hasConflict;
    },

    async saveBooking(booking: Booking) {
      await delay(MOCK_DELAY);
      // Conflict check should be called before this, but good to have here too?
      // Let's assume conflict check is done in UI or separated.
      if (!booking.id) {
        booking.id = 'b' + Date.now();
        this.bookings.push(booking);
      } else {
        const idx = this.bookings.findIndex(b => b.id === booking.id);
        if (idx !== -1) this.bookings[idx] = booking;
      }
    },

    async verifyConversion(bookingId: string) {
      await delay(MOCK_DELAY);
      const b = this.bookings.find(x => x.id === bookingId);
      if (b && b.type === 'Trial' && b.status === 'Completed') {
        b.isConverted = true;
        ElMessage.success('Verification Successful');
      }
    },

    // --- Students ---
    async activateStudent(id: string) {
      await delay(MOCK_DELAY);
      const s = this.students.find(x => x.id === id);
      if (s && s.contractUrl) {
        s.type = 'Regular';
        ElMessage.success('Student Activated');
      }
    },

    // --- Roles ---
    async saveRole(role: RoleDef) {
      await delay(MOCK_DELAY);
      if (role.id === 'super_admin') {
        throw new Error('Cannot modify Super Admin role directly.');
      }

      const idx = this.roles.findIndex(r => r.id === role.id);
      if (idx > -1) {
        this.roles[idx] = { ...role, updatedAt: dayjs().toISOString() };
        ElMessage.success('Role updated');
      } else {
        const newRole: RoleDef = {
          ...role,
          id: 'r' + Date.now(),
          updatedAt: dayjs().toISOString()
        };
        this.roles.push(newRole);
        ElMessage.success('Role created');
      }
    },

    async deleteRole(id: string) {
      await delay(MOCK_DELAY);
      if (id === 'super_admin') {
        ElMessage.error('Cannot delete Super Admin');
        return;
      }
      this.roles = this.roles.filter(r => r.id !== id);
      ElMessage.success('Role deleted');
    }
  },
});
