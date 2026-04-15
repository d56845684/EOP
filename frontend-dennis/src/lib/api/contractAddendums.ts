import { fetchWithAuth } from './fetchWithAuth'
import { API_BASE_URL } from './config'
import { apiGet, apiPost, apiPut, apiDelete } from './client'

export type AddendumStatus = 'pending' | 'active' | 'expired' | 'terminated'
export type ContractType = 'student' | 'teacher'

export interface ContractAddendum {
    id: string
    addendum_no: string
    contract_type: ContractType
    parent_contract_id: string
    original_end_date: string
    new_end_date: string
    addendum_status: AddendumStatus
    file_path?: string
    file_name?: string
    file_uploaded_at?: string
    notes?: string
    created_at?: string
    updated_at?: string
    parent_contract_no?: string
    person_name?: string
}

export interface CreateAddendumData {
    new_end_date: string
    notes?: string
}

export interface UpdateAddendumData {
    new_end_date?: string
    notes?: string
}

function contractBasePath(contractType: ContractType): string {
    return contractType === 'student' ? 'student-contracts' : 'teacher-contracts'
}

export const contractAddendumsApi = {
    list: (contractType: ContractType, contractId: string) =>
        apiGet<ContractAddendum[]>(
            `/api/v1/${contractBasePath(contractType)}/${contractId}/addendums`,
            '取得附約列表失敗',
        ),

    create: (contractType: ContractType, contractId: string, data: CreateAddendumData) =>
        apiPost<ContractAddendum>(
            `/api/v1/${contractBasePath(contractType)}/${contractId}/addendums`,
            data,
            '建立附約失敗',
        ),

    update: (contractType: ContractType, contractId: string, addendumId: string, data: UpdateAddendumData) =>
        apiPut<ContractAddendum>(
            `/api/v1/${contractBasePath(contractType)}/${contractId}/addendums/${addendumId}`,
            data,
            '更新附約失敗',
        ),

    delete: (contractType: ContractType, contractId: string, addendumId: string) =>
        apiDelete(
            `/api/v1/${contractBasePath(contractType)}/${contractId}/addendums/${addendumId}`,
            '刪除附約失敗',
        ),

    async generatePdf(contractType: ContractType, contractId: string, addendumId: string): Promise<{ success: boolean, error: any }> {
        try {
            const base = contractBasePath(contractType)
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/${base}/${contractId}/addendums/${addendumId}/generate-pdf`, {
                method: 'GET',
            })
            if (!response.ok) {
                const error = await response.json()
                return { success: false, error: { message: error.detail || '產生附約 PDF 失敗' } }
            }
            const blob = await response.blob()
            const contentDisposition = response.headers.get('Content-Disposition')
            let filename = 'addendum.pdf'
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^"]+)"?/)
                if (match) filename = match[1]
            }
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
            return { success: true, error: null }
        } catch (err) {
            return { success: false, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async uploadFile(contractType: ContractType, contractId: string, addendumId: string, file: File): Promise<{ data: ContractAddendum | null, error: any }> {
        try {
            const base = contractBasePath(contractType)
            const fileExt = file.name.split('.').pop()?.toLowerCase() || 'pdf'

            const urlRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/${base}/${contractId}/addendums/${addendumId}/upload-url?file_ext=${fileExt}`, {
                method: 'POST',
            })
            if (!urlRes.ok) {
                const error = await urlRes.json()
                return { data: null, error: { message: error.detail || '取得上傳連結失敗' } }
            }
            const { upload_url, storage_path, content_type } = await urlRes.json()

            const uploadRes = await fetch(upload_url, {
                method: 'PUT',
                headers: { 'Content-Type': content_type || file.type || 'application/octet-stream' },
                body: file,
            })
            if (!uploadRes.ok) {
                const errText = await uploadRes.text()
                return { data: null, error: { message: `檔案上傳失敗: ${errText}` } }
            }

            // 3. 通知 backend 確認上傳完成
            const confirmRes = await fetchWithAuth(`${API_BASE_URL}/api/v1/${base}/${contractId}/addendums/${addendumId}/confirm-upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storage_path, file_name: file.name }),
            })
            if (!confirmRes.ok) {
                const error = await confirmRes.json()
                return { data: null, error: { message: error.detail || '確認上傳失敗' } }
            }

            const result = await confirmRes.json()
            return { data: result.data || null, error: null }
        } catch (err) {
            return { data: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },

    async downloadFile(contractType: ContractType, contractId: string, addendumId: string): Promise<{ url: string | null, error: any }> {
        try {
            const base = contractBasePath(contractType)
            const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/${base}/${contractId}/addendums/${addendumId}/download-url`, {
                method: 'GET',
            })
            if (!response.ok) {
                const error = await response.json()
                return { url: null, error: { message: error.detail || '取得下載連結失敗' } }
            }
            const { download_url } = await response.json()
            return { url: download_url, error: null }
        } catch (err) {
            return { url: null, error: { message: '網路錯誤，請稍後再試' } }
        }
    },
}
