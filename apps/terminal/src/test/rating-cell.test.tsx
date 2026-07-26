import { RatingCell } from "@/components/rating-cell";
import { TooltipProvider } from "@/components/ui/tooltip";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const wrap = (ui: React.ReactNode) => render(<TooltipProvider>{ui}</TooltipProvider>);

describe("RatingCell", () => {
  it("renders the letter with its interval attached", () => {
    wrap(<RatingCell letter="BB" lo="BBB-" hi="BB-" basis="GRID_INTERIOR" />);
    expect(screen.getByTestId("letter-with-interval")).toHaveTextContent("BB (BBB-..BB-)");
    expect(screen.getByText(/derived conversion/i)).toBeInTheDocument();
  });

  it("explains an absent letter with the determination", () => {
    wrap(<RatingCell letter={null} lo={null} hi={null} determination="NOT_RATED" />);
    expect(screen.getByLabelText("no letter")).toHaveTextContent("NOT_RATED");
  });
});
