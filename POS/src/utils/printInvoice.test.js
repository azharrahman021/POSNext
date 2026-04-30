import { beforeEach, describe, expect, it, vi } from "vitest"
import { printWithSilentFallback, silentPrintInvoice } from "./printInvoice"

const mocks = vi.hoisted(() => ({
	call: vi.fn(),
	printHTML: vi.fn(),
	warn: vi.fn(),
	error: vi.fn(),
	info: vi.fn(),
}))

vi.mock("@/utils/apiWrapper", () => ({
	call: mocks.call,
}))

vi.mock("@/utils/qzTray", () => ({
	printHTML: mocks.printHTML,
}))

vi.mock("@/utils/logger", () => ({
	logger: {
		create: () => ({
			warn: mocks.warn,
			error: mocks.error,
			info: mocks.info,
		}),
	},
}))

describe("printInvoice silent printing", () => {
	beforeEach(() => {
		vi.clearAllMocks()
		mocks.printHTML.mockResolvedValue(true)
	})

	it("uses the invoice POS Profile print format and letterhead for silent printing", async () => {
		mocks.call.mockImplementation((method, args) => {
			if (method === "pos_next.api.invoices.get_invoice") {
				expect(args).toEqual({ invoice_name: "ACC-SINV-0001" })
				return Promise.resolve({ name: "ACC-SINV-0001", pos_profile: "Main POS" })
			}

			if (method === "frappe.client.get") {
				expect(args).toEqual({ doctype: "POS Profile", name: "Main POS" })
				return Promise.resolve({
					print_format: "Custom Thermal Receipt",
					letter_head: "Store Letterhead",
				})
			}

			if (method === "frappe.www.printview.get_html_and_style") {
				expect(args).toEqual({
					doc: "Sales Invoice",
					name: "ACC-SINV-0001",
					print_format: "Custom Thermal Receipt",
					no_letterhead: 0,
					letterhead: "Store Letterhead",
				})
				return Promise.resolve({ html: "<div>Receipt</div>", style: "body{width:80mm}" })
			}

			throw new Error(`Unexpected method ${method}`)
		})

		const result = await printWithSilentFallback({ name: "ACC-SINV-0001" })

		expect(result).toEqual({ method: "silent", success: true })
		expect(mocks.printHTML).toHaveBeenCalledWith(expect.stringContaining("<div>Receipt</div>"))
	})

	it("falls back to POS Next Receipt when invoice settings cannot be fetched", async () => {
		mocks.call.mockImplementation((method, args) => {
			if (method === "pos_next.api.invoices.get_invoice") {
				return Promise.reject(new Error("network unavailable"))
			}

			if (method === "frappe.www.printview.get_html_and_style") {
				expect(args).toEqual({
					doc: "Sales Invoice",
					name: "ACC-SINV-0002",
					print_format: "POS Next Receipt",
					no_letterhead: 1,
				})
				return Promise.resolve({ html: "<div>Default receipt</div>", style: "" })
			}

			throw new Error(`Unexpected method ${method}`)
		})

		const result = await printWithSilentFallback({ name: "ACC-SINV-0002" })

		expect(result).toEqual({ method: "silent", success: true })
		expect(mocks.warn).toHaveBeenCalledWith(
			"Could not fetch invoice print settings, using defaults:",
			"network unavailable"
		)
	})

	it("passes letterhead options to Frappe when silent printing directly", async () => {
		mocks.call.mockResolvedValue({ html: "<div>Receipt</div>", style: "" })

		await silentPrintInvoice("ACC-SINV-0003", "Custom Thermal Receipt", "Store Letterhead")

		expect(mocks.call).toHaveBeenCalledWith("frappe.www.printview.get_html_and_style", {
			doc: "Sales Invoice",
			name: "ACC-SINV-0003",
			print_format: "Custom Thermal Receipt",
			no_letterhead: 0,
			letterhead: "Store Letterhead",
		})
	})
})
