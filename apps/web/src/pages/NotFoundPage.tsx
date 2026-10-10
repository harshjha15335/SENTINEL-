import { Link } from "react-router-dom";

import { EmptyState } from "@/components/ui/States";

export function NotFoundPage() {
  return (
    <EmptyState title="Page not found" action={<Link to="/" className="text-sm text-accent hover:underline">Back to Command Center</Link>}>
      The address does not match any SENTINEL screen.
    </EmptyState>
  );
}
