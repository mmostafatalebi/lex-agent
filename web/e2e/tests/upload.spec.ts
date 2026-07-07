import { expect, test } from "@playwright/test";

import { mockUploadAndReview } from "../mocks";

const PDF = { name: "sample.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") };

test("landing page renders the headline", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Review a contract in five minutes." })
  ).toBeVisible();
});

test("dropping a valid PDF routes to the analysis page", async ({ page }) => {
  await mockUploadAndReview(page, { threadId: "mock-thread-id" });
  await page.goto("/");
  await page.getByTestId("file-input").setInputFiles(PDF);
  await page.waitForURL("**/analyses/mock-thread-id");
  await expect(page).toHaveURL(/\/analyses\/mock-thread-id$/);
});

test("an invalid file type is rejected without navigating", async ({ page }) => {
  await mockUploadAndReview(page);
  await page.goto("/");
  await page.getByTestId("file-input").setInputFiles({
    name: "photo.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("not a contract"),
  });
  await expect(page.getByText("Only PDF or DOCX files are supported.")).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
});

test("a file over 6MB is rejected without navigating", async ({ page }) => {
  await mockUploadAndReview(page);
  await page.goto("/");
  await page.getByTestId("file-input").setInputFiles({
    name: "big.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(6 * 1024 * 1024 + 1, 0),
  });
  await expect(page.getByText(/The limit is 6MB/)).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
});
