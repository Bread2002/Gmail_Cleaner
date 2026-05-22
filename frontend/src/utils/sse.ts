/**
 * Typed EventSource wrapper with automatic cleanup.
 *
 * EventSource auto-reconnects by default when the connection drops — we stop
 * that by closing it explicitly on terminal events (done, complete, error).
 */

export interface SSEHandlers<T = unknown> {
  onMessage: (type: string, data: T) => void;
  onDone?: () => void;
  onError?: (err: Event) => void;
}

export interface SSEHandle {
  close: () => void;
}

export function createSSE<T = unknown>(
  url: string,
  handlers: SSEHandlers<T>,
): SSEHandle {
  const es = new EventSource(url);

  // Whether we closed intentionally — suppresses spurious onerror after close()
  let closedIntentionally = false;

  const close = () => {
    closedIntentionally = true;
    es.close();
  };

  // Named events the backend emits
  const namedEvents = ['progress', 'sender_found', 'complete', 'error', 'done'];

  for (const type of namedEvents) {
    es.addEventListener(type, (evt: Event) => {
      let data: T;
      try {
        data = JSON.parse((evt as MessageEvent).data);
      } catch {
        data = {} as T;
      }

      if (type === 'done') {
        // "done" is the sentinel the backend sends after scan/trash completes
        handlers.onDone?.();
        close();
        return;
      }

      if (type === 'complete') {
        // Backend emits "complete" inside the task, then "done" from the generator
        // We handle both — call onMessage first so the hook can log it, then close
        handlers.onMessage(type, data);
        handlers.onDone?.();
        close();
        return;
      }

      if (type === 'error') {
        // Terminal error from the backend task — notify and close so we don't reconnect
        handlers.onMessage(type, data);
        close();
        return;
      }

      handlers.onMessage(type, data);
    });
  }

  es.onerror = (err) => {
    if (closedIntentionally) return;   // ignore errors from our own close()
    handlers.onError?.(err);
    close();  // stop auto-reconnect on unexpected drops
  };

  return { close };
}
