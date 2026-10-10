import { useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { useAuth } from "../contexts/AuthContext";
import { useAddSegmentComment, useDeleteSegmentComment } from "../hooks/useProjects";
import type { SegmentCommentResponse } from "../api/client";

interface CommentsPanelProps {
  projectId: string;
  segmentId: string;
  comments: SegmentCommentResponse[];
  isApproved?: boolean;
}

export function CommentsPanel({ projectId, segmentId, comments, isApproved }: CommentsPanelProps) {
  const { user } = useAuth();
  const [newComment, setNewComment] = useState("");
  const addMutation = useAddSegmentComment();
  const deleteMutation = useDeleteSegmentComment();

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    addMutation.mutate(
      { projectId, segmentId, text: newComment },
      {
        onSuccess: () => setNewComment(""),
      }
    );
  };

  const handleDeleteComment = (commentId: string) => {
    if (confirm("Are you sure you want to delete this comment?")) {
      deleteMutation.mutate({ projectId, segmentId, commentId });
    }
  };

  return (
    <div className="bg-muted/30 border-t p-4 rounded-b-xl space-y-4 shadow-inner" data-testid="comments-panel">
      {comments.length > 0 ? (
        <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
          {comments.map((comment) => {
            const isOwner = user?.id === comment.user_id;
            const isAdmin = user?.role === "admin";
            const canDelete = (isOwner || isAdmin) && !isApproved;
            
            return (
              <div key={comment.id} className="bg-background rounded-lg p-3 border shadow-sm text-sm">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-medium text-xs text-muted-foreground flex items-center gap-2">
                    <span className="truncate max-w-[150px] inline-block font-semibold text-foreground">
                      {comment.user?.email || "Unknown user"}
                    </span>
                    <span>&bull;</span>
                    <span>{new Date(comment.created_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}</span>
                  </div>
                  {canDelete && (
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      onClick={() => handleDeleteComment(comment.id)}
                      disabled={deleteMutation.isPending && deleteMutation.variables?.commentId === comment.id}
                      title="Delete comment"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <div className="whitespace-pre-wrap break-words">{comment.text}</div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground italic py-2 text-center">
          No comments yet. Be the first to start the discussion!
        </div>
      )}

      {!isApproved && (
        <div className="flex items-start gap-2 pt-2 border-t border-border/50">
          <Textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment..."
            className="min-h-[40px] h-[40px] max-h-[120px] resize-y text-sm py-2"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAddComment();
              }
            }}
          />
          <Button 
            onClick={handleAddComment} 
            disabled={!newComment.trim() || addMutation.isPending}
            size="icon"
            className="shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
