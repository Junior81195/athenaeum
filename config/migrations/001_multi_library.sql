-- Migration: Multi-library conversations
-- Allows conversations to span multiple libraries

ALTER TABLE conversations ALTER COLUMN library_id DROP NOT NULL;

CREATE TABLE IF NOT EXISTS conversation_libraries (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    PRIMARY KEY (conversation_id, library_id)
);
CREATE INDEX IF NOT EXISTS idx_convlibs_conv ON conversation_libraries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_convlibs_lib ON conversation_libraries(library_id);
