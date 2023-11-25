#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from numpy.linalg import inv


class Block:
    """A base class circuit block, which represents electrical currents.

    This is the primary data structure in ACORN as it is described in Giuliano
    (1963). It combines four different matrices: a document-term matrix (C),
    its transpose (B), a document-document matrix (E), and a term-term matrix
    (D).

    When composed, the full Block looks like this:

        [[E, C],
         [B, D]]

    A Block is a square matrix. Its dimensions are the sum of C's length and
    width.

    See the `.compose()` and `.decompose()` methods for information about how a
    Block's matrices are put together and broken apart when querying ACORN for
    document and word associations.

    References
    ----------
    Giuliano, Vincent E. “Analog Networks for Word Association.” IEEE
        Transactions on Military Electronics MIL–7, no. 2/3 (April 1963):
        221–34. https://doi.org/10.1109/TME.1963.4323077.
    """

    def __init__(self, data: np.ndarray) -> None:
        """Construct the Block.

        Parameters
        ----------
        data
            A two-dimensional array upon which to base the Block components
        """
        # First, ensure that we're working with NumPy arrays
        if not isinstance(data, np.ndarray):
            data = np.asarray(data, dtype="float32")

        # Block metadata. The attributes `.m` and `.n` refer to the number of
        # documents and terms, respectively. The `.size` attribute is the full
        # length/width of the Block, and `.kind` is a flag for the repr
        self.m, self.n = data.shape
        self.size = self.m + self.n
        self.kind = "base"

        # Build the primary Block components. See the `.compose()` method
        self.C = data.copy().astype("float32")
        self.B = self.C.T
        self.E = self.C @ self.B
        self.D = self.B @ self.C

        # The full Block
        self.G = np.zeros((self.size, self.size), dtype="float32")

    def __repr__(self) -> str:
        """Block repr."""
        return f"A ({self.size} x {self.size}) {self.kind} block."

    @property
    def state(self) -> np.ndarray:
        """The current state of the Block."""
        return self.G

    def compose(self, **kwargs) -> None:
        """Compose the Block.

        This gathers together the E, C, B, and D matrices and arranges in them
        in a big matrix.

        Different query methods require certain alterations to the Block's
        components (e.g. normalization, zeroed-out portions of the Block). This
        method should be called by those queries to produce the appropriate
        components before associations are calculated. Similarly, child classes
        should compose the Block during construction if their `.__init__()`
        methods differ from the parent class. The parent class does not run a
        Block composition when initialized; instead, it creates a (size x size)
        matrix of 0s.

        If a Block is composed without any arguments, it will pull from its
        original matrices. Re-compose the Block at the end of a query or other
        operation to return the Block to its initializing state.

        Composing the Block is equation 1 in Giuliano (1963).

        Parameters
        ----------
        kwargs
            Optionally include the E, C, B, or D matrices
        """
        E, C = kwargs.get("E", self.E), kwargs.get("C", self.C)
        B, D = kwargs.get("B", self.B), kwargs.get("D", self.D)
        self.G = np.block([[E, C], [B, D]])

    def decompose(self) -> tuple[np.ndarray]:
        """Decompose the Block into its constituent parts.

        Run a Block decomposition whenever you want to access the component
        matrices after they've been modified in some way by a query.

        Returns
        -------
        E, C, B, D
            Separated parts of the Block
        """
        E = self.G[: self.m, : self.m]
        C = self.G[: self.m, self.m :]
        B = self.G[self.m :, : self.m]
        D = self.G[self.m :, self.m :]

        return E, C, B, D


class ResistorBlock(Block):
    """A leak resistor Block.

    Each document and term in the data has a corresponding resistor, which
    applies a normalization value. This Block performs that normalization and
    then builds a matrix where λ = normed terms and γ = normed documents:

        [[λ, 0],
         [0, γ]]

    The row sums of the final matrix should have row sums normalized to unity
    or less. The same goes for when a ResistorBlock is used to normalize a
    ConectionBlock (see the latter's `.compose()` function).

    This is the Λ matrix in equation 9 of Giuliano (1963).
    """

    def __init__(self, data: np.ndarray, norm_by: float = 1.0) -> None:
        """Construct the Block.

        Parameters
        ----------
        data
            A two-dimensional array upon which to base the ResistorBlock
            components
        norm_by
            Normalization (0, 1) on the resistors
        """
        super().__init__(data=data)
        self.kind = "resistor"

        # Set the normalization value and normalize the term-term and
        # document-document matrices
        self.norm_by = norm_by
        self.E = self._term_norm()
        self.D = self._doc_norm()

        # The other two matrices contain 0s
        self.C = np.zeros_like(self.C)
        self.B = np.zeros_like(self.B)

        # Run a composition because the components have changed
        self.compose()

    def _term_norm(self) -> np.ndarray:
        """Compute normalization values for the terms.

        Use the result of this function as a drop-in for E in the final Block
        composition.

        This is equation 7 in Giuliano (1963).

        Returns
        -------
        eq7
            A diagonal matrix of normalized term values
        """
        eq7 = 1 / (self.norm_by + np.sum(self.E, 1) + np.sum(self.C, 1))
        eq7 = np.diag(eq7)

        return eq7

    def _doc_norm(self) -> np.ndarray:
        """Compute normalization values for the documents.

        Use the result of this function as a drop-in for D in the final Block
        composition.

        Returns
        -------
        eq8
            A diagonal matrix of normalized document values
        """
        eq8 = 1 / (self.norm_by + np.sum(self.B, 1) + np.sum(self.D))
        eq8 = np.diag(eq8)

        return eq8


class ConnectionBlock(Block):
    """A connection Block, which represents electrical conductances in a
    circuit.

    All queries are made with this class. Unlike the base Block class, a
    ConnectionBlock retains the values of its input data and exposes methods
    for making queries.

    A ConnectionBlock is normalized by a ResistorBlock. This operation is
    implemented in the ConnectionBlock's `.compose()` method. Query methods may
    also update the norming value for the ResistorBlock, which will in turn
    update the ConnectionBlock's state.
    """

    def __init__(self, DTM: np.ndarray, norm_by: float = 1.0) -> None:
        """Construct the Block.

        Parameters
        ----------
        DTM
            The document-term matrix (a two-dimensional array of value counts)
        norm_by
            Normalization (0, 1) to apply
        """
        # Run the Block's constructor
        super().__init__(data=DTM)
        self.kind = "connection"

        # Build identity matrices sized to document and term counts. We use
        # these to compute associations
        self.Idoc = np.identity(self.m, dtype="float32")
        self.Iterm = np.identity(self.n, dtype="float32")

        # Set the normalization value and compose the ConnectionBlock
        self.norm_by = norm_by
        self.compose()

    def compose(self, **kwargs) -> None:
        """Compose the ConnectionBlock.

        In addition to gathering together the E, C, B, and D matrices, this
        method applies normalization from a ResistorBlock.

        Parameters
        ----------
        kwargs
            Optionally include the E, C, B, or D matrices as well as a
            normalization value (`norm_by`)
        """
        # Run a composition
        super().compose(**kwargs)

        # Get the normalization value. Then construct a ResistorBlock
        norm_by = kwargs.get("norm_by", self.norm_by)
        Λ = ResistorBlock(self.C, norm_by=norm_by)

        # Normalize with values from the ResistorBlock
        self.G = Λ.state @ self.G

    def _validate_query(self, Q: np.ndarray) -> np.ndarray:
        """Validate a query.

        A valid query is one with a length of self.n slots, which contain
        either 0s or 1s.

        Parameters
        ----------
        Q
            The query vector

        Raises
        ------
        ValueError
            If the query length does not match the number of unique terms or if
            the query contains numbers others than 0 or 1
        """
        if not isinstance(Q, np.ndarray):
            Q = np.asarray(Q, dtype="float32")

        if len(Q) != self.n:
            raise ValueError(f"Query length must be {self.n}")

        if not np.all((Q == 0) | (Q == 1)):
            raise ValueError("Query must contain 0 or 1 for all slots")

        return Q

    def _set_state(self, norm_by: float, **kwargs) -> None:
        """Set the state with a normalization value and optional matrices.

        Parameters
        ---------
        norm_by
            Normalization (0, 1) for the Block
        kwargs
            Any other arguments for Block composition
        """
        close = np.isclose(self.norm_by, norm_by)
        if not close and kwargs:
            self.compose(norm_by=norm_by, **kwargs)
        elif not close and not kwargs:
            self.compose(norm_by=norm_by)
        elif close and kwargs:
            self.compose(**kwargs)
        else:
            pass

    def query(self, Q: np.ndarray, norm_by: float = 1.0) -> np.ndarray:
        """Find document associations for a query.

        A query is a num_term-length (self.n) array of 0s and 1s. 1 means a
        term has been selected, while 0 is a deselected term. The resultant
        associations are a num_doc-length (self.m) array of floats.

        This is equation 12 in Giuliano (1963).

        Parameters
        ----------
        Q
            The query vector
        norm_by
            Normalization (0, 1) for the Block

        Returns
        -------
        A
            Document association values for the query
        """
        # Validate the query and check whether we need to re-compose
        Q = self._validate_query(Q)
        self._set_state(norm_by)

        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        eq12a = inv(self.Idoc - E) @ (C @ inv(self.Iterm - D))
        eq12b = inv(
            self.Iterm - (B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D))
        )

        # Re-compose the Block from the initializing data if we're working with
        # a different `norm_by` than the initializing one
        if not np.isclose(self.norm_by, norm_by):
            self.compose()

        return eq12a @ eq12b @ Q

    def query_DTM(self, Q: np.ndarray, norm_by: float = 1.0) -> np.ndarray:
        """Query document associations assuming no information about term-term
        or document-document interaction is available.

        This is equation 13 in Giuliano (1963).

        Parameters
        ----------
        Q
            The query vector
        norm_by
            Normalization (0, 1) values for the Block

        Returns
        -------
        A
            Document association values for the query
        """
        # Validate the query. Then, since we're discounting any information
        # we'd otherwise gain from the document-document and term-term
        # matrices, set the state with zeroed-out versions of them
        Q = self._validate_query(Q)
        self._set_state(
            E=np.zeros_like(self.E), D=np.zeros_like(self.D), norm_by=norm_by
        )

        # Decompose the Block and build the pieces of the equation
        E, C, B, D = self.decompose()

        eq13 = C @ inv(self.Iterm - (B @ C))

        # Re-compose the Block from the initializing data
        self.compose()

        return eq13 @ Q

    def word_associations(self) -> np.ndarray:
        """Find word-word associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        A
            Word associations
        """
        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        eq12a = inv(self.Iterm - D)
        eq12b = inv(
            self.Iterm - ((B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D)))
        )

        return eq12a @ eq12b

    def document_associations(self) -> np.ndarray:
        """Find document-document associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        A
            Document associations
        """
        # Decompose the Block and retrieve the document-document matrix
        E, *_ = self.decompose()

        return inv(self.Idoc - E)
