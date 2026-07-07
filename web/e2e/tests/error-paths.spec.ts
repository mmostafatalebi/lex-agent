import { expect, test } from "@playwright/test";

import { mockStatusError } from "../mocks";

test("a 500 from the status endpoint shows the error boundary with retry", async ({ page }) => {
  await mockStatusError(page, 500);
  await page.goto("/analyses/t-500");
  await expect(page.getByTestId("error-boundary")).toBeVisible();
  await expect(page.getByTestId("retry-button")).toBeVisible();
});

test("a 404 from the status endpoint shows the not-found page", async ({ page }) => {
  await mockStatusError(page, 404);
  await page.goto("/analyses/nonexistent");
  await expect(page.getByTestId("not-found")).toBeVisible();
});

test("the api key gate blocks upload when a key is required", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("lexagent.requireApiKey", "true");
  });
  await page.goto("/");
  await expect(page.getByTestId("api-key-gate")).toBeVisible();
  await expect(page.getByTestId("upload-zone")).toHaveCount(0);
});
