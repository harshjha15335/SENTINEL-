import { Link } from "react-router-dom";
export function NotFoundPage() {
  return (
    <section className="workspace-not-found">
      <p className="workspace-kicker">404 / END OF THIS TRAIL</p>
      <h1>
        That page has moved
        <br />
        out of sight.
      </h1>
      <p>The address does not match a SENTINEL workspace.</p>
      <div>
        <Link className="command-review-button" to="/app">
          Back to Command Center
        </Link>
        <Link to="/" className="text-accent">
          Follow the Money homepage
        </Link>
      </div>
    </section>
  );
}
