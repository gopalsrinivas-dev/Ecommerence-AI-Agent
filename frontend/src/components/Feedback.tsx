import { ApiError } from "@/lib/api-client";
export function Feedback({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="error" role="alert">
      <p>{error.message}</p>
      {retry && <button onClick={retry}>Try again</button>}
      {error instanceof ApiError && error.requestId && (
        <details>
          <summary>Support details</summary>Request ID: {error.requestId}
        </details>
      )}
    </div>
  );
}
export function Badge({ status }: { status: string }) {
  return (
    <span className={`badge ${status.toLowerCase()}`}>
      {status.toLowerCase().replace("_", " ")}
    </span>
  );
}
