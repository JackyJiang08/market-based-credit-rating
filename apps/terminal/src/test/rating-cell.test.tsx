import { RatingCell } from "@/components/rating-cell";
import { TooltipProvider } from "@/components/ui/tooltip";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const wrap = (ui: React.ReactNode) => render(<TooltipProvider>{ui}</TooltipProvider>);

describe("RatingCell", () => {
  it("renders the letter with its interval attached; basis is an icon-badge", () => {
    wrap(<RatingCell letter="BB" lo="BBB-" hi="BB-" basis="GRID_INTERIOR" />);
    expect(screen.getByTestId("letter-with-interval")).toHaveTextContent("BB (BBB-..BB-)");
    // the basis moved out of the text into a small badge with a full aria-label
    expect(
      screen.getByLabelText(/derived conversion — basis: Grid lookup/i),
    ).toBeInTheDocument();
    // no machine constant in the visible cell text
    expect(screen.queryByText("GRID_INTERIOR")).not.toBeInTheDocument();
  });

  it("explains an absent letter with the humanized determination", () => {
    wrap(<RatingCell letter={null} lo={null} hi={null} determination="NOT_RATED" />);
    expect(screen.getByLabelText("no letter")).toHaveTextContent("Not rated");
    expect(screen.getByLabelText("no letter")).not.toHaveTextContent("NOT_RATED");
  });
});
