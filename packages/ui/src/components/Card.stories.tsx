import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect } from "storybook/test";
import { I18nProvider } from "../i18n";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./Card";

const meta = {
  title: "Design System/Card",
  component: Card,
  parameters: { a11y: { test: "error" } },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ResultSummary: Story = {
  render: () => (
    <Card>
      <CardHeader>
        <CardTitle>Result summary</CardTitle>
        <CardDescription>Evidence and uncertainty for clinician review.</CardDescription>
      </CardHeader>
      <CardContent><p>A negative result does not exclude involvement.</p></CardContent>
    </Card>
  ),
};

export const RightToLeft: Story = {
  render: () => (
    <I18nProvider direction="rtl">
      <Card>
        <CardHeader><CardTitle>Right-to-left direction sample</CardTitle></CardHeader>
        <CardContent><p>This checks layout direction only; it is not translated patient content.</p></CardContent>
      </Card>
    </I18nProvider>
  ),
  play: async ({ canvasElement }) => {
    await expect(canvasElement.querySelector('[dir="rtl"]')).not.toBeNull();
  },
};
