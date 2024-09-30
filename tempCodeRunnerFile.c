#include <stdio.h>
#include <stdlib.h>

// Define the structure for a node in the linked list
typedef struct Node {
    int coeff;
    int exp;
    struct Node* next;
} Node;

// Function to create a new node
Node* createNode(int coeff, int exp) {
    Node* newNode = (Node*)malloc(sizeof(Node));
    if (!newNode) {
        printf("Memory error\n");
        return NULL;
    }
    newNode->coeff = coeff;
    newNode->exp = exp;
    newNode->next = NULL;
    return newNode;
}

// Function to insert a term into the polynomial
void insertTerm(Node** head, int coeff, int exp) {
    Node* newNode = createNode(coeff, exp);
    if (*head == NULL || (*head)->exp < exp) {
        newNode->next = *head;
        *head = newNode;
    } else {
        Node* current = *head;
        while (current->next != NULL && current->next->exp > exp) {
            current = current->next;
        }
        newNode->next = current->next;
        current->next = newNode;
    }
}

// Function to add two polynomials
Node* addPolynomials(Node* poly1, Node* poly2) {
    Node* result = NULL;
    Node* current1 = poly1;
    Node* current2 = poly2;

    while (current1 != NULL && current2 != NULL) {
        if (current1->exp == current2->exp) {
            int coeff = current1->coeff + current2->coeff;
            if (coeff != 0) {
                insertTerm(&result, coeff, current1->exp);
            }
            current1 = current1->next;
            current2 = current2->next;
        } else if (current1->exp > current2->exp) {
            insertTerm(&result, current1->coeff, current1->exp);
            current1 = current1->next;
        } else {
            insertTerm(&result, current2->coeff, current2->exp);
            current2 = current2->next;
        }
    }

    // Add remaining terms from poly1
    while (current1 != NULL) {
        insertTerm(&result, current1->coeff, current1->exp);
        current1 = current1->next;
    }

    // Add remaining terms from poly2
    while (current2 != NULL) {
        insertTerm(&result, current2->coeff, current2->exp);
        current2 = current2->next;
    }

    return result;
}

// Function to print a polynomial
void printPoly(Node* poly) {
    while (poly != NULL) {
        printf("%dx^%d + ", poly->coeff, poly->exp);
        poly = poly->next;
    }
    printf("\n");
}

int main() {
    Node* poly1 = NULL;
    Node* poly2 = NULL;

    // Create first polynomial: 3x^2 + 2x + 1
    insertTerm(&poly1, 3, 2);
    insertTerm(&poly1, 2, 1);
    insertTerm(&poly1, 1, 0);

    // Create second polynomial: 2x^2 + x + 4
    insertTerm(&poly2, 2, 2);
    insertTerm(&poly2, 1, 1);
    insertTerm(&poly2, 4, 0);

    printf("Polynomial 1: ");
    printPoly(poly1);

    printf("Polynomial 2: ");
    printPoly(poly2);

    Node* result = addPolynomials(poly1, poly2);

    printf("Result: ");
    printPoly(result);

    return 0;
}
