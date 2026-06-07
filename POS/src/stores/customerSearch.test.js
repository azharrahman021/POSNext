import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"

const callMock = vi.fn()
const searchCachedCustomersMock = vi.fn()
const cacheCustomersMock = vi.fn()
const deleteCustomersMock = vi.fn()
const localStorageState = new Map()

globalThis.localStorage = {
	clear: vi.fn(() => localStorageState.clear()),
	getItem: vi.fn((key) => localStorageState.get(key) ?? null),
	removeItem: vi.fn((key) => localStorageState.delete(key)),
	setItem: vi.fn((key, value) => localStorageState.set(key, String(value))),
}

vi.mock("@/utils/apiWrapper", () => ({
	call: callMock,
}))

vi.mock("@/utils/offline", () => ({
	isOffline: () => false,
}))

vi.mock("@/utils/offline/workerClient", () => ({
	offlineWorker: {
		searchCachedCustomers: searchCachedCustomersMock,
		cacheCustomers: cacheCustomersMock,
		deleteCustomers: deleteCustomersMock,
	},
}))

vi.mock("@/utils/logger", () => ({
	logger: {
		create: () => ({
			debug: vi.fn(),
			error: vi.fn(),
			info: vi.fn(),
			success: vi.fn(),
			warn: vi.fn(),
		}),
	},
}))

vi.mock("@/composables/useRealtimeCustomers", () => ({
	useRealtimeCustomers: () => ({
		onCustomerUpdate: vi.fn(),
	}),
}))

describe("customerSearch store", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		localStorage.clear()
		vi.clearAllMocks()
		searchCachedCustomersMock.mockResolvedValue([])
		cacheCustomersMock.mockResolvedValue()
		deleteCustomersMock.mockResolvedValue()
	})

	it("falls back to a full sync when local customer cache is empty", async () => {
		const customers = [
			{
				name: "Cash Sale",
				customer_name: "Cash Sale",
				disabled: 0,
			},
		]
		callMock.mockResolvedValue(customers)
		localStorage.setItem("pos_customers_last_sync", "2026-06-01T00:00:00.000Z")

		const { useCustomerSearchStore } = await import("./customerSearch")
		const store = useCustomerSearchStore()

		await store.loadAllCustomers("Fix & Build Margin Free Store -Karanthad")

		expect(callMock).toHaveBeenCalledWith(
			"pos_next.api.customers.get_customers",
			{
				pos_profile: "Fix & Build Margin Free Store -Karanthad",
				search_term: "",
				start: 0,
				limit: 0,
				modified_since: null,
			},
		)
		expect(store.allCustomers).toEqual(customers)
		expect(cacheCustomersMock).toHaveBeenCalledWith(customers)
	})
})
