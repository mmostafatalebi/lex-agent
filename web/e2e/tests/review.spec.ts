import { expect, test } from "@playwright/test";

import { CANNED_FLAGS, mockUploadAndReview } from "../mocks";

test("renders one card per flag", async ({ page }) => {
  await mockUploadAndReview(page, { threadId: "t-review" });
  await page.goto("/analyses/t-review");
  await expect(page.getByTestId("flag-card")).toHaveCount(CANNED_FLAGS.length);
});

test("accepting all flags submits and shows redlines", async ({ page }) => {
  await mockUploadAndReview(page, { threadId: "t-accept" });
  await page.goto("/analyses/t-accept");

  const cards = page.getByTestId("flag-card");
  await expect(cards).toHaveCount(3);
  for (let i = 0; i < 3; i += 1) {
    await cards.nth(i).getByTestId("accept-flag").click();
  }
  await page.getByTestId("submit-decisions").click();

  await expect(page.getByTestId("redline-list")).toBeVisible();
  await expect(page.getByTestId("redline-diff")).toHaveCount(3);
});

test("rejecting all flags submits and shows zero redlines", async ({ page }) => {
  await mockUploadAndReview(page, { threadId: "t-reject" });
  await page.goto("/analyses/t-reject");

  const cards = page.getByTestId("flag-card");
  await expect(cards).toHaveCount(3);
  for (let i = 0; i < 3; i += 1) {
    await cards.nth(i).getByTestId("reject-flag").click();
  }
  await page.getByTestId("submit-decisions").click();

  await expect(page.getByTestId("redline-summary")).toContainText("0 flags accepted");
  await expect(page.getByTestId("redline-diff")).toHaveCount(0);
});
