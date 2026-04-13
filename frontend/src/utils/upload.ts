import { uploadStudentContract, confirmUploadContract, uploadStudentContractAddendum, confirmuploadStudentContractAddendum } from '@/api/studentContract';
import { uploadTeacherContract, confirmUploadTeacherContract, uploadTeacherContractAddendum, confirmUploadTeacherContractAddendum } from '@/api/teacherContract';
import { confirmUploadDetail, getUploadDetailUrl } from '@/api/teacherDetails';
import { getTeacherAvatarUploadUrl, confirmTeacherAvatar } from '@/api/teacher';

export const uploadContractFile = async (role: 'teacher' | 'student', contractId: string, addendumId: string | null, file: File) => {
  if (!contractId) {
    throw new Error('Contract ID is required');
  }
  try {
    let urlRes;
    if (addendumId) {
      const useApi = role === 'teacher' ? uploadTeacherContractAddendum : uploadStudentContractAddendum;
      urlRes = await useApi(contractId, addendumId);
    } else {
      const useApi = role === 'teacher' ? uploadTeacherContract : uploadStudentContract;
      urlRes = await useApi(contractId);
    }
    const { upload_url, storage_path, content_type } = urlRes;
    const uploadRes = await fetch(upload_url, {
      method: 'PUT',
      headers: {
        'Content-Type': content_type,
      },
      mode: 'cors',
      credentials: 'omit',
      body: file,
    });
    if (!uploadRes.ok) {
      throw new Error('Upload failed');
    }
    let confirmRes
    if (addendumId) {
      const useApi = role === 'teacher' ? confirmUploadTeacherContractAddendum : confirmuploadStudentContractAddendum;
      confirmRes = await useApi(contractId, addendumId, { storage_path, file_name: file.name });
    } else {
      const useApi = role === 'teacher' ? confirmUploadTeacherContract : confirmUploadContract;
      confirmRes = await useApi(contractId, { storage_path, file_name: file.name });
    }
    return confirmRes;
  } catch (error) {
    throw error;
  }
}

export const uploadDetailFile = async (detailId: string, file: File) => {
  if (!detailId) {
    throw new Error('Detail ID is required');
  }
  try {
    const urlRes = await getUploadDetailUrl(detailId, { file_name: file.name });
    const { upload_url, storage_path, content_type } = urlRes;
    const uploadRes = await fetch(upload_url, {
      method: 'PUT',
      headers: {
        'Content-Type': content_type,
      },
      body: file,
    });
    if (!uploadRes.ok) {
      throw new Error('Upload failed');
    }
    const confirmRes = await confirmUploadDetail(detailId, { storage_path, file_name: file.name });
    return confirmRes;
  } catch (error) {
    throw error;
  }
}

export const uploadTeacherAvatar = async (teacherId: string, file: File) => {
  if (!teacherId) {
    throw new Error('Teacher ID is required');
  }
  try {
    const urlRes = await getTeacherAvatarUploadUrl(teacherId, { file_name: file.name });
    const { upload_url, storage_path, content_type } = urlRes;
    const uploadRes = await fetch(upload_url, {
      method: 'PUT',
      headers: {
        'Content-Type': content_type,
      },
      body: file,
    });
    if (!uploadRes.ok) {
      throw new Error('Upload failed');
    }
    const confirmRes = await confirmTeacherAvatar(teacherId, { storage_path, file_name: file.name });
    return confirmRes;
  } catch (error) {
    throw error;
  }
}
