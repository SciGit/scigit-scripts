service RepositoryManager {
	void addPublicKey(1: i32 keyId, 2: i32 userId, 3: string publicKey),
	void deletePublicKey(1: i32 keyId, 2: i32 userId, 3: string publicKey),
	void createRepository(1: i32 repositoryId),
	void deleteRepository(1: i32 repositoryId)
}
