"""Operations verified against https://developers.buffer.com/reference.md."""

POST_FIELDS = """
    id text channelId channelService status dueAt sentAt
    shareMode schedulingType externalLink createdAt updatedAt
    error { message supportUrl }
"""

ACCOUNT = "query BufferAccount { account { id } }"
ORGANIZATIONS = """
query BufferOrganizations {
  account { organizations { id name channelCount } }
}
"""
CHANNELS = """
query BufferChannels($input: ChannelsInput!) {
  channels(input: $input) {
    id name displayName service type organizationId timezone
    isDisconnected isLocked isQueuePaused externalLink
  }
}
"""
POSTS = (
    """
query BufferPosts($input: PostsInput!, $first: Int!, $after: String) {
  posts(input: $input, first: $first, after: $after) {
    edges { node { %s } }
    pageInfo { hasNextPage endCursor }
  }
}
"""
    % POST_FIELDS
)
POST = (
    """
query BufferPost($input: PostInput!) {
  post(input: $input) { %s }
}
"""
    % POST_FIELDS
)
CREATE_POST = (
    """
mutation BufferCreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess { post { %s } }
    ... on MutationError { message }
  }
}
"""
    % POST_FIELDS
)
EDIT_POST = (
    """
mutation BufferEditPost($input: EditPostInput!) {
  editPost(input: $input) {
    __typename
    ... on PostActionSuccess { post { %s } }
    ... on MutationError { message }
  }
}
"""
    % POST_FIELDS
)
DELETE_POST = """
mutation BufferDeletePost($input: DeletePostInput!) {
  deletePost(input: $input) {
    __typename
    ... on DeletePostSuccess { id }
    ... on MutationError { message }
  }
}
"""
